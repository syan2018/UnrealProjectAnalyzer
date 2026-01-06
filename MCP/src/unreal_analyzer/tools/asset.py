"""
Asset analysis tools.

These tools communicate with the Unreal Plugin HTTP API to query
asset references, referencers, and metadata.
"""

from ..ue_client import get_client
from ..ue_client.http_client import UEPluginError


def _ue_error(tool: str, e: Exception) -> dict:
    """Return a friendly, structured error for UE Plugin connectivity issues."""
    return {
        "ok": False,
        "error": f"UE Plugin API 调用失败（{tool}）",
        "detail": str(e),
        "hint": "请确认 UE 编辑器已启动且启用了 UnrealProjectAnalyzer 插件。",
    }


async def search_assets(name_pattern: str, asset_type: str = "") -> dict:
    """
    Search assets by name pattern and optional type filter (UE plugin required).

    Args:
        name_pattern: Asset name pattern. Supports UE wildcards like `*` and `?`.
        asset_type: Optional asset class filter (substring match).

    Returns:
        A dict:
        - ok: bool
        - matches: list[dict] with {name, path, type}
        - count: int
    """
    client = get_client()
    try:
        return await client.get(
            "/asset/search",
            {
                "pattern": name_pattern,
                "type": asset_type,
            },
        )
    except UEPluginError as e:
        return _ue_error("search_assets", e)


async def get_asset_references(asset_path: str) -> dict:
    """
    Get outgoing references of an asset (UE plugin required).

    Args:
        asset_path: Asset package path (e.g. `/Game/...`).

    Returns:
        A dict:
        - ok: bool
        - asset: str
        - references: list[str]
        - count: int
    """
    client = get_client()
    # NOTE: asset_path contains "/" (e.g. "/Game/..."), so pass via query params.
    try:
        return await client.get("/asset/references", {"asset_path": asset_path})
    except UEPluginError as e:
        return _ue_error("get_asset_references", e)


async def get_asset_referencers(asset_path: str) -> dict:
    """
    Get incoming referencers of an asset (UE plugin required).

    Args:
        asset_path: Asset package path (e.g. `/Game/...`).

    Returns:
        A dict:
        - ok: bool
        - asset: str
        - referencers: list[str]
        - count: int
    """
    client = get_client()
    try:
        return await client.get("/asset/referencers", {"asset_path": asset_path})
    except UEPluginError as e:
        return _ue_error("get_asset_referencers", e)


async def get_asset_metadata(asset_path: str) -> dict:
    """
    Get basic metadata of an asset (UE plugin required).

    Args:
        asset_path: Asset package path (e.g. `/Game/...`).

    Returns:
        A dict:
        - ok: bool
        - name: str
        - path: str
        - type: str
        - size: number (optional)
        - object_path: str
    """
    client = get_client()
    try:
        return await client.get("/asset/metadata", {"asset_path": asset_path})
    except UEPluginError as e:
        return _ue_error("get_asset_metadata", e)
