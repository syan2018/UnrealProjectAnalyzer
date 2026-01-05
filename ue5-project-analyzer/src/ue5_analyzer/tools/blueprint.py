"""
Blueprint analysis tools.

These tools communicate with the UE5 Plugin HTTP API to query
Blueprint metadata, hierarchy, dependencies, and graph information.
"""

from ..ue_client import get_client


async def search_blueprints(name_pattern: str, class_filter: str = "") -> dict:
    """Search for blueprints by name pattern.
    
    Args:
        name_pattern: Blueprint name or partial name (supports wildcards *)
        class_filter: Optional parent class filter (e.g., "Actor", "GameplayAbility")
    
    Returns:
        Dictionary containing:
        - matches: List of matching blueprints with name and path
        - count: Number of matches
    """
    client = get_client()
    return await client.get("/blueprint/search", {
        "pattern": name_pattern,
        "class": class_filter,
    })


async def get_blueprint_hierarchy(bp_path: str) -> dict:
    """Get the class inheritance hierarchy of a blueprint.
    
    Args:
        bp_path: Blueprint asset path (e.g., "/Game/Blueprints/BP_Player")
    
    Returns:
        Dictionary containing:
        - hierarchy: List of classes from blueprint to UObject
        - native_parent: First native C++ parent class
        - blueprint_parents: List of blueprint parent classes
    """
    client = get_client()
    return await client.get(f"/blueprint/{bp_path}/hierarchy")


async def get_blueprint_dependencies(bp_path: str) -> dict:
    """Get all dependencies of a blueprint.
    
    Args:
        bp_path: Blueprint asset path
    
    Returns:
        Dictionary containing:
        - dependencies: List of dependencies with class, module, and type
        - summary: Count by dependency type
    """
    client = get_client()
    return await client.get(f"/blueprint/{bp_path}/dependencies")


async def get_blueprint_referencers(bp_path: str) -> dict:
    """Get all assets that reference this blueprint.
    
    Args:
        bp_path: Blueprint asset path
    
    Returns:
        Dictionary containing:
        - referencers: List of referencing assets
        - count: Number of referencers
    """
    client = get_client()
    return await client.get(f"/blueprint/{bp_path}/referencers")


async def get_blueprint_graph(bp_path: str, graph_name: str = "EventGraph") -> dict:
    """Get the node graph of a blueprint.
    
    Args:
        bp_path: Blueprint asset path
        graph_name: Name of the graph (default: "EventGraph")
    
    Returns:
        Dictionary containing:
        - nodes: List of nodes with id, type, and connections
        - connections: List of pin connections
    """
    client = get_client()
    return await client.get(f"/blueprint/{bp_path}/graph/{graph_name}")


async def get_blueprint_details(bp_path: str) -> dict:
    """Get comprehensive details of a blueprint.
    
    Args:
        bp_path: Blueprint asset path
    
    Returns:
        Dictionary containing:
        - variables: List of variables
        - functions: List of functions
        - components: List of components
        - graphs: List of graph names
        - parent_class: Parent class info
    """
    client = get_client()
    return await client.get(f"/blueprint/{bp_path}/details")
