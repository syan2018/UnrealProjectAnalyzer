"""
Asset analysis tools.

These tools communicate with the UE5 Plugin HTTP API to query
asset references, referencers, and metadata.
"""

from ..ue_client import get_client


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
    return await client.get("/asset/search", {
        "pattern": name_pattern,
        "type": asset_type,
    })


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
    return await client.get(f"/asset/{asset_path}/references")


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
    return await client.get(f"/asset/{asset_path}/referencers")


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
    return await client.get(f"/asset/{asset_path}/metadata")
