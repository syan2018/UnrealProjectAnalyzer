"""
Cross-domain query tools.

Only a minimal subset is exposed by the MCP server:
- trace_reference_chain
- find_cpp_class_usage
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


async def trace_reference_chain(
    start_asset: Annotated[str, "Starting asset path (e.g. '/Game/...')"],
    max_depth: Annotated[int, "Maximum depth to trace (default: 3)"] = 3,
    direction: Annotated[Literal["references", "referencers", "both"], "Trace direction"] = "both",
) -> dict:
    """
    Trace a cross-domain reference chain (UE plugin required).

    Args:
        start_asset: Starting asset path (e.g. `/Game/...`).
        max_depth: Max recursion depth.
        direction: `references` | `referencers` | `both`.

    Returns:
        A dict:
        - ok: bool
        - start: str
        - direction: str
        - max_depth: int
        - chain: dict (nested children)
        - unique_nodes: int

    Notes:
        Uses UE-side async job + chunked retrieval to avoid socket_send_failure for large payloads.
    """
    client = get_client()
    try:
        # Use get_with_async for automatic async job handling
        return await client.get_with_async(
            "/analysis/reference-chain",
            {
                "start": start_asset,
                "depth": max_depth,
                "direction": direction,
            },
            timeout_s=120.0,  # Large reference chains may take time
        )
    except UEPluginError as e:
        return _ue_error("trace_reference_chain", e)


async def find_cpp_class_usage(
    cpp_class: Annotated[str, "C++ class name (e.g. 'ULyraHealthSet')"],
    *,
    scope: Annotated[Literal["project", "engine", "all"], "C++ search scope"] = "project",
    include_cpp: Annotated[bool, "Include C++ references (default: True)"] = True,
    max_cpp_results: Annotated[int, "Max number of C++ matches to return"] = 200,
) -> dict:
    """
    Find usage of a C++ class across Blueprint/Asset and C++ code.

    Args:
        cpp_class: C++ class name (e.g. `ULyraHealthSet`).
        scope: C++ search scope: `project` | `engine` | `all`.
        include_cpp: Whether to include C++ references (default: True).
        max_cpp_results: Max C++ matches to return.

    Returns:
        UE plugin part:
        - as_parent_class: list[dict]
        - as_component: list
        - as_variable_type: list
        - as_function_call: list

        C++ part (when include_cpp=True):
        - cpp_references: list[dict]
        - cpp_reference_count: int
        - cpp_reference_truncated: bool
        - cpp_scope: str
    """
    client = get_client()
    try:
        bp_result = await client.get(
            "/analysis/cpp-class-usage",
            {
                "class": cpp_class,
            },
        )
        if not include_cpp:
            return bp_result

        # Merge in C++ references (scope-aware).
        try:
            from ..cpp_analyzer import get_analyzer

            analyzer = get_analyzer()
            cpp_result = await analyzer.find_references(
                cpp_class,
                scope=scope,
            )
            # Truncate to avoid huge payloads
            matches = cpp_result.get("matches", [])[: max(0, int(max_cpp_results))]
            bp_result["cpp_references"] = matches
            bp_result["cpp_reference_count"] = len(matches)
            bp_result["cpp_reference_truncated"] = cpp_result.get("count", 0) > len(matches)
            bp_result["cpp_scope"] = scope
        except Exception as e:
            bp_result["cpp_references"] = []
            bp_result["cpp_reference_count"] = 0
            bp_result["cpp_error"] = str(e)

        return bp_result
    except UEPluginError as e:
        return _ue_error("find_cpp_class_usage", e)
