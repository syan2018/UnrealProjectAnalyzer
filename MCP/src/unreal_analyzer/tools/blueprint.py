"""
Blueprint analysis tools.

These tools communicate with the Unreal Plugin HTTP API to query
Blueprint metadata, hierarchy, dependencies, and graph information.
"""

from typing import Annotated, Literal

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


def _convert_to_mermaid(graph_data: dict) -> str:
    """
    Convert Blueprint graph JSON to Mermaid flowchart format.

    Args:
        graph_data: The raw graph data with nodes and connections.

    Returns:
        Mermaid flowchart string.
    """
    lines = ["flowchart TD"]

    nodes = graph_data.get("nodes", [])
    connections = graph_data.get("connections", [])

    # Build node ID to title map
    node_titles = {}
    for node in nodes:
        node_id = node.get("id", "")
        # Sanitize title for Mermaid (escape special chars)
        title = node.get("title", node.get("type", "Unknown"))
        # Truncate long titles
        if len(title) > 40:
            title = title[:37] + "..."
        # Escape characters that might break Mermaid
        title = title.replace('"', "'").replace("[", "(").replace("]", ")")
        node_titles[node_id] = title

        # Determine node shape based on type
        node_type = node.get("type", "")
        if "Event" in node_type or "Input" in node_type:
            # Events use stadium shape
            lines.append(f'    {node_id}(["{title}"])')
        elif "Return" in node_type or "Output" in node_type:
            # Outputs use double-circle (subroutine)
            lines.append(f'    {node_id}[["{title}"]]')
        elif "Branch" in node_type or "Switch" in node_type:
            # Conditionals use diamond - escape braces
            lines.append("    " + node_id + '{{"' + title + '"}}')
        elif "Function" in node_type or "Call" in node_type:
            # Function calls use rounded rect
            lines.append(f'    {node_id}("{title}")')
        else:
            # Default: rectangle
            lines.append(f'    {node_id}["{title}"]')

    # Add connections
    lines.append("")
    lines.append("    %% Connections")
    for conn in connections:
        from_node = conn.get("from_node", "")
        to_node = conn.get("to_node", "")
        from_pin = conn.get("from_pin", "")
        to_pin = conn.get("to_pin", "")

        if from_node and to_node:
            # Determine connection style based on pin type
            if "exec" in from_pin.lower() or "then" in from_pin.lower():
                # Execution flow: thick arrow
                lines.append(f"    {from_node} ==> {to_node}")
            else:
                # Data flow: regular arrow with label
                label = from_pin if from_pin else ""
                if label:
                    lines.append(f'    {from_node} -->|"{label}"| {to_node}')
                else:
                    lines.append(f"    {from_node} --> {to_node}")

    return "\n".join(lines)


def _generate_graph_summary(graph_data: dict) -> dict:
    """
    Generate a human-readable summary of the graph.

    Args:
        graph_data: The raw graph data.

    Returns:
        Summary dict with node categories and key flows.
    """
    nodes = graph_data.get("nodes", [])
    connections = graph_data.get("connections", [])

    # Categorize nodes
    events = []
    functions = []
    variables = []
    flow_control = []
    others = []

    for node in nodes:
        node_type = node.get("type", "")
        title = node.get("title", "")

        if "Event" in node_type or "Input" in node_type:
            events.append(title)
        elif "Function" in node_type or "Call" in node_type:
            functions.append(title)
        elif "Variable" in node_type or "Get" in node_type or "Set" in node_type:
            variables.append(title)
        elif "Branch" in node_type or "Sequence" in node_type or "Switch" in node_type:
            flow_control.append(title)
        else:
            others.append(title)

    return {
        "total_nodes": len(nodes),
        "total_connections": len(connections),
        "events": events[:10],  # Limit to avoid huge output
        "functions": functions[:20],
        "variables": variables[:10],
        "flow_control": flow_control[:10],
        "event_count": len(events),
        "function_count": len(functions),
        "variable_count": len(variables),
    }


async def get_blueprint_graph(
    bp_path: Annotated[str, "Blueprint asset path. Example: '/Game/BP_Player'"],
    graph_name: Annotated[str, "Graph name (default: 'EventGraph')."] = "EventGraph",
    format: Annotated[
        Literal["mermaid", "summary", "json"],
        "Output format: 'mermaid' (default) | 'summary' | 'json'.",
    ] = "mermaid",
) -> dict:
    """
    Get Blueprint graph (EventGraph/function graphs) (UE plugin required).

    Returns graph data in the specified format. Large graphs use async retrieval.
    """
    client = get_client()
    try:
        # Use get_with_async for automatic async job handling (large graphs)
        raw_result = await client.get_with_async(
            "/blueprint/graph",
            {"bp_path": bp_path, "graph_name": graph_name},
            timeout_s=60.0,
        )

        # If not ok, return as-is
        if not raw_result.get("ok", False):
            return raw_result

        # Format output
        if format == "json":
            return raw_result
        elif format == "summary":
            return {
                "ok": True,
                "blueprint": raw_result.get("blueprint"),
                "graph": raw_result.get("graph"),
                "summary": _generate_graph_summary(raw_result),
            }
        else:  # mermaid
            return {
                "ok": True,
                "blueprint": raw_result.get("blueprint"),
                "graph": raw_result.get("graph"),
                "mermaid": _convert_to_mermaid(raw_result),
                "summary": _generate_graph_summary(raw_result),
            }

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
        - soft_reference_count: int (if any soft refs found)
        - soft_reference_hint: str (if any soft refs found)
    """
    client = get_client()
    try:
        return await client.get("/blueprint/details", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_details", e)


async def get_blueprint_soft_references(bp_path: str) -> dict:
    """
    Get soft references from Blueprint CDO (Class Default Object) (UE plugin required).

    Soft references are asset references stored in Blueprint variable defaults that
    are NOT tracked by AssetRegistry.GetDependencies(). This is useful for finding
    hidden dependencies like TSubclassOf<> defaults.

    Args:
        bp_path: Blueprint asset path (e.g. '/Game/Blueprints/BP_Player').

    Returns:
        A dict containing:
        - ok: bool
        - blueprint: str
        - soft_references: list[dict] (each with path, name, type)
        - count: int
        - note: str (explanation of what soft references are)
    """
    client = get_client()
    try:
        return await client.get("/blueprint/soft-references", {"bp_path": bp_path})
    except UEPluginError as e:
        return _ue_error("get_blueprint_soft_references", e)
