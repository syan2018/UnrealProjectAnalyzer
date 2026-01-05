"""
Cross-domain query tools.

These tools combine Blueprint, Asset, and C++ analysis to provide
comprehensive cross-domain queries.
"""

from ..ue_client import get_client
from ..cpp_analyzer import get_analyzer


async def trace_reference_chain(
    start_asset: str,
    max_depth: int = 3,
    direction: str = "both"
) -> dict:
    """Trace the reference chain from an asset.
    
    Args:
        start_asset: Starting asset path
        max_depth: Maximum depth to trace (default: 3)
        direction: "references", "referencers", or "both"
    
    Returns:
        Dictionary containing:
        - root: Starting asset info
        - chain: Nested reference tree
        - summary: Statistics about the chain
    """
    client = get_client()
    return await client.get("/analysis/reference-chain", {
        "start": start_asset,
        "depth": max_depth,
        "direction": direction,
    })


async def find_cpp_class_usage(cpp_class: str) -> dict:
    """Find all Blueprint/Asset usage of a C++ class.
    
    Args:
        cpp_class: C++ class name (e.g., "UCharacterMovementComponent")
    
    Returns:
        Dictionary containing:
        - as_parent_class: Blueprints inheriting from this class
        - as_component: Blueprints using this as a component
        - as_variable_type: Blueprints with variables of this type
        - as_function_call: Blueprints calling functions from this class
    """
    client = get_client()
    return await client.get("/analysis/cpp-class-usage", {
        "class": cpp_class,
    })
