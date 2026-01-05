"""
Blueprint analysis tools.

These tools communicate with the Unreal Plugin HTTP API to query
Blueprint metadata, hierarchy, dependencies, and graph information.
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
    try:
        return await client.get("/blueprint/search", {
            "pattern": name_pattern,
            "class": class_filter,
        })
    except UEPluginError as e:
        return _ue_error("search_blueprints", e)


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
    # NOTE: bp_path contains "/" (e.g. "/Game/..."), so passing it in the URL path
    # will break typical HTTP router segment matching. Use query params instead.
    try:
        return await client.get("/blueprint/hierarchy", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_hierarchy", e)


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
    try:
        return await client.get("/blueprint/dependencies", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_dependencies", e)


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
    try:
        return await client.get("/blueprint/referencers", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_referencers", e)


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
    try:
        return await client.get("/blueprint/graph", {"bp_path": bp_path, "graph_name": graph_name})
    except UEPluginError as e:
        return _ue_error("get_blueprint_graph", e)


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
    try:
        return await client.get("/blueprint/details", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_details", e)
