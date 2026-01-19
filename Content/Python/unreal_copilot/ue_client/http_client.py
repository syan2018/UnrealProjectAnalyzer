"""
HTTP Client for Unreal Plugin API.

Supports automatic async job handling for large responses to avoid socket_send_failure.
"""

import asyncio
import json
import time
from urllib.parse import quote

import httpx

from ..config import get_config


class UEPluginClient:
    """HTTP client for communicating with Unreal Plugin."""

    def __init__(self, base_url: str | None = None, timeout: float = 60.0):
        """Initialize the client.

        Args:
            base_url: Base URL of the Unreal plugin API (default from config)
            timeout: Request timeout in seconds (increased to 60s for large responses)
        """
        self.base_url = base_url or get_config().ue_plugin_url
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, path: str, params: dict | None = None) -> dict:
        """Make a GET request.

        Args:
            path: API path (may contain asset paths that need encoding)
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            UEPluginError: If the request fails
        """
        client = await self._get_client()

        # Encode asset paths in the URL
        encoded_path = self._encode_path(path)

        try:
            response = await client.get(encoded_path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise UEPluginError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise UEPluginError(f"Request failed: {e}") from e

    async def post(self, path: str, data: dict | None = None) -> dict:
        """Make a POST request.

        Args:
            path: API path
            data: JSON body

        Returns:
            JSON response as dictionary
        """
        client = await self._get_client()
        encoded_path = self._encode_path(path)

        try:
            response = await client.post(encoded_path, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise UEPluginError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise UEPluginError(f"Request failed: {e}") from e

    def _encode_path(self, path: str) -> str:
        """Encode asset paths in the URL.

        Asset paths like /Game/Blueprints/BP_Player need special handling.
        """
        # Split path and encode asset path segments
        parts = path.split("/")
        encoded_parts = []

        for part in parts:
            # Don't encode empty parts or known API segments
            if not part or part in ("blueprint", "asset", "analysis", "health"):
                encoded_parts.append(part)
            else:
                encoded_parts.append(quote(part, safe=""))

        return "/".join(encoded_parts)

    async def health_check(self) -> dict:
        """Check if the Unreal Plugin is running.

        Returns:
            Health status dictionary with 'ok', 'status', 'ue_version' fields

        Raises:
            UEPluginError: If the plugin is not running or unreachable
        """
        try:
            return await self.get("/health")
        except UEPluginError as e:
            raise UEPluginError(
                f"UE Plugin is not running or unreachable. "
                f"Ensure UE Editor is running with plugin enabled. Error: {e}"
            ) from e

    async def is_available(self) -> bool:
        """Check if the Unreal Plugin is available (non-throwing).

        Returns:
            True if the plugin is running, False otherwise
        """
        try:
            await self.health_check()
            return True
        except UEPluginError:
            return False

    # -------------------------------------------------------------------------
    # Async job support (for large responses)
    # -------------------------------------------------------------------------
    async def get_with_async(
        self,
        path: str,
        params: dict | None = None,
        *,
        timeout_s: float = 120.0,
        poll_interval_s: float = 0.1,
        chunk_size: int = 65536,
    ) -> dict:
        """Make a GET request with automatic async job handling.

        If the server returns an async job envelope (mode='async', job_id=...),
        this method will automatically poll for completion and fetch the result
        in chunks to avoid socket_send_failure on large responses.

        Args:
            path: API path
            params: Query parameters
            timeout_s: Maximum time to wait for async job completion
            poll_interval_s: Interval between status polls
            chunk_size: Maximum characters per chunk when fetching result

        Returns:
            Final JSON response (either direct or reassembled from chunks)

        Raises:
            UEPluginError: If the request fails or times out
        """
        # First request - may return direct result or async job envelope
        response = await self.get(path, params)

        # Check if it's an async job envelope
        if (
            isinstance(response, dict)
            and response.get("mode") == "async"
            and response.get("job_id")
        ):
            return await self._fetch_async_job(
                job_id=str(response["job_id"]),
                timeout_s=timeout_s,
                poll_interval_s=poll_interval_s,
                chunk_size=chunk_size,
            )

        # Direct response
        return response

    async def _fetch_async_job(
        self,
        job_id: str,
        *,
        timeout_s: float = 120.0,
        poll_interval_s: float = 0.1,
        chunk_size: int = 65536,
    ) -> dict:
        """Fetch result from an async job via chunked retrieval.

        Args:
            job_id: The async job ID
            timeout_s: Maximum time to wait for job completion
            poll_interval_s: Interval between status polls
            chunk_size: Maximum characters per chunk

        Returns:
            Reassembled JSON result

        Raises:
            UEPluginError: If job fails or times out
        """
        start_t = time.monotonic()

        # Poll for job completion
        while True:
            status = await self.get("/analysis/job/status", {"id": job_id})
            state = status.get("status")

            if state == "done":
                total_chars = int(status.get("total_chars", 0))
                break

            if state == "error":
                raise UEPluginError(f"Async job failed: {status.get('error', 'Unknown error')}")

            if (time.monotonic() - start_t) > timeout_s:
                raise UEPluginError(
                    f"Async job timeout after {timeout_s}s (id={job_id}, status={state})"
                )

            await asyncio.sleep(poll_interval_s)

        # Fetch result in chunks
        chunks: list[str] = []
        offset = 0

        while offset < total_chars:
            part = await self.get(
                "/analysis/job/result",
                {
                    "id": job_id,
                    "offset": offset,
                    "limit": chunk_size,
                },
            )
            chunks.append(part.get("chunk", ""))
            offset = int(part.get("next_offset", offset + chunk_size))

            if part.get("done", False):
                break

        # Reassemble and parse JSON
        try:
            return json.loads("".join(chunks))
        except json.JSONDecodeError as e:
            raise UEPluginError(f"Failed to parse async job result: {e}") from e


class UEPluginError(Exception):
    """Error from Unreal Plugin API."""

    pass


# Global client instance
_client: UEPluginClient | None = None


def get_client() -> UEPluginClient:
    """Get the global client instance."""
    global _client
    if _client is None:
        _client = UEPluginClient()
    return _client


def set_client(client: UEPluginClient) -> None:
    """Set the global client instance."""
    global _client
    _client = client
