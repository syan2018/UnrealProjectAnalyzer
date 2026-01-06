"""
Blueprint analysis tools.

These tools communicate with the Unreal Plugin HTTP API to query
Blueprint metadata, hierarchy, dependencies, and graph information.
"""

from typing import Annotated

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


async def search_blueprints(name_pattern: str, class_filter: str = "") -> dict:
    """
    Search Blueprints by name pattern (UE plugin required).

    Args:
        name_pattern: Blueprint name pattern. Supports UE wildcards like `*` and `?`.
        class_filter: Optional parent class filter (substring match).

    Returns:
        A dict:
        - ok: bool
        - matches: list[dict] with {name, path, type}
        - count: int

    Notes:
        - This tool is kept for specialized needs; for most workflows prefer `search()`.
        - Paths are package paths like `/Game/...`.
    """
    client = get_client()
    try:
        return await client.get(
            "/blueprint/search",
            {
                "pattern": name_pattern,
                "class": class_filter,
            },
        )
    except UEPluginError as e:
        return _ue_error("search_blueprints", e)


async def get_blueprint_hierarchy(bp_path: str) -> dict:
    """
    Get the Blueprint inheritance chain (UE plugin required).

    Args:
        bp_path: Blueprint asset path (e.g. `/Game/Blueprints/BP_Player`).

    Returns:
        A dict:
        - ok: bool
        - blueprint: str
        - hierarchy: list[dict] (name/path/is_native)
        - native_parent: str
        - blueprint_parents: list[dict]
    """
    client = get_client()
    # NOTE: bp_path contains "/" (e.g. "/Game/..."), so passing it in the URL path
    # will break typical HTTP router segment matching. Use query params instead.
    try:
        return await client.get("/blueprint/hierarchy", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_hierarchy", e)


async def get_blueprint_dependencies(bp_path: str) -> dict:
    """
    Get outgoing dependencies of a Blueprint (UE plugin required).

    Args:
        bp_path: Blueprint asset path.

    Returns:
        A dict:
        - ok: bool
        - blueprint: str
        - dependencies: list[str]
        - count: int
    """
    client = get_client()
    try:
        return await client.get("/blueprint/dependencies", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_dependencies", e)


async def get_blueprint_referencers(bp_path: str) -> dict:
    """
    Get incoming referencers of a Blueprint (UE plugin required).

    Args:
        bp_path: Blueprint asset path.

    Returns:
        A dict:
        - ok: bool
        - blueprint: str
        - referencers: list[str]
        - count: int
    """
    client = get_client()
    try:
        return await client.get("/blueprint/referencers", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_referencers", e)


async def get_blueprint_graph(
    bp_path: Annotated[str, "Blueprint path (e.g. '/Game/...')"],
    graph_name: Annotated[str, "Graph name (default: EventGraph)"] = "EventGraph",
) -> dict:
    """
    获取蓝图图表（节点 + 连接）（需要 UE 插件）。

    说明：
        - `bp_path` 必须是 `/Game/...` 这种 package path
        - 大图会自动走异步任务 + 分块拉取，避免 UE http socket_send_failure
    """
    client = get_client()
    try:
        # Use get_with_async for automatic async job handling (large graphs)
        return await client.get_with_async(
            "/blueprint/graph",
            {"bp_path": bp_path, "graph_name": graph_name},
            timeout_s=60.0,
        )
    except UEPluginError as e:
        return _ue_error("get_blueprint_graph", e)


async def get_blueprint_details(bp_path: str) -> dict:
    """
    Get Blueprint details (variables, functions, components) (UE plugin required).

    Args:
        bp_path: Blueprint asset path.

    Returns:
        A dict containing:
        - ok: bool
        - blueprint: str
        - variables: list[dict]
        - functions: list[str]
        - components: list[dict]
        - graphs: list[str]
        - parent_class: dict
        - variable_count: int
        - function_count: int
        - component_count: int
    """
    client = get_client()
    try:
        return await client.get("/blueprint/details", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_details", e)
