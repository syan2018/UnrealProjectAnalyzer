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
        "hint": "请确认 UE 编辑器已启动且启用了 UnrealProjectAnalyzer 插件，并检查 UE_PLUGIN_HOST/UE_PLUGIN_PORT 配置。",
    }


async def search_assets(name_pattern: str, asset_type: str = "") -> dict:
    """Search for assets by name and type.
    
    Args:
        name_pattern: Asset name or partial name (supports wildcards *)
        asset_type: Optional asset type filter (e.g., "Blueprint", "SkeletalMesh")
    
    Returns:
        Dictionary containing:
        - matches: List of matching assets with name, path, and type
        - count: Number of matches
    """
    client = get_client()
    try:
        return await client.get("/asset/search", {
            "pattern": name_pattern,
            "type": asset_type,
        })
    except UEPluginError as e:
        return _ue_error("search_assets", e)


async def get_asset_references(asset_path: str) -> dict:
    """Get all assets referenced by this asset.
    
    Args:
        asset_path: Asset path (e.g., "/Game/Characters/SK_Mannequin")
    
    Returns:
        Dictionary containing:
        - references: List of referenced assets
        - count: Number of references
    """
    client = get_client()
    # NOTE: asset_path contains "/" (e.g. "/Game/..."), so pass via query params.
    try:
        return await client.get("/asset/references", {"asset_path": asset_path})
    except UEPluginError as e:
        return _ue_error("get_asset_references", e)


async def get_asset_referencers(asset_path: str) -> dict:
    """Get all assets that reference this asset.
    
    Args:
        asset_path: Asset path
    
    Returns:
        Dictionary containing:
        - referencers: List of referencing assets
        - count: Number of referencers
        - by_type: Breakdown by asset type
    """
    client = get_client()
    try:
        return await client.get("/asset/referencers", {"asset_path": asset_path})
    except UEPluginError as e:
        return _ue_error("get_asset_referencers", e)


async def get_asset_metadata(asset_path: str) -> dict:
    """Get metadata of an asset.
    
    Args:
        asset_path: Asset path
    
    Returns:
        Dictionary containing:
        - name: Asset name
        - path: Full asset path
        - type: Asset class type
        - size: File size (if available)
        - last_modified: Last modification time
    """
    client = get_client()
    try:
        return await client.get("/asset/metadata", {"asset_path": asset_path})
    except UEPluginError as e:
        return _ue_error("get_asset_metadata", e)
