"""
HTTP Client for UE5 Plugin API.
"""

import httpx
from urllib.parse import quote

from ..config import get_config


class UEPluginClient:
    """HTTP client for communicating with UE5 Plugin."""
    
    def __init__(self, base_url: str | None = None, timeout: float = 30.0):
        """Initialize the client.
        
        Args:
            base_url: Base URL of the UE5 plugin API (default from config)
            timeout: Request timeout in seconds
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
            if not part or part in ("blueprint", "asset", "analysis"):
                encoded_parts.append(part)
            else:
                encoded_parts.append(quote(part, safe=""))
        
        return "/".join(encoded_parts)


class UEPluginError(Exception):
    """Error from UE5 Plugin API."""
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
