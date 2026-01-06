"""
Cross-domain query tools.

Only a minimal subset is exposed by the MCP server:
- trace_reference_chain
- find_cpp_class_usage
"""

from pathlib import Path
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


def _aggregate_cpp_references(
    matches: list[dict], class_name: str, max_lines_per_file: int = 3
) -> list[dict]:
    """
    Aggregate C++ references by file, distinguishing definition from usage.

    Args:
        matches: Raw matches from find_references.
        class_name: The class being searched for (to detect definition file).
        max_lines_per_file: Max individual lines to show per file.

    Returns:
        Aggregated reference list with file-level grouping.
    """
    # Group by file
    by_file: dict[str, list[dict]] = {}
    for match in matches:
        file_path = match.get("file", "")
        if not file_path:
            continue
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(match)

    aggregated = []
    # Strip common prefixes like 'U', 'A', 'F' for matching header files
    stripped_name = class_name
    if class_name and class_name[0] in ("U", "A", "F", "I", "E", "T", "S"):
        stripped_name = class_name[1:]

    for file_path, file_matches in by_file.items():
        file_name = Path(file_path).name
        stem = Path(file_path).stem

        # Detect if this is the definition file
        is_definition_file = False
        if stem == class_name or stem == stripped_name:
            is_definition_file = True
        elif f"{stripped_name}.h" in file_name or f"{stripped_name}.cpp" in file_name:
            is_definition_file = True

        # Sort by line number
        file_matches.sort(key=lambda m: m.get("line", 0))

        # Aggregate consecutive lines
        line_ranges = []
        current_start = None
        current_end = None

        for match in file_matches:
            line = match.get("line", 0)
            if current_start is None:
                current_start = current_end = line
            elif line <= current_end + 3:  # Within 3 lines = consecutive
                current_end = line
            else:
                line_ranges.append((current_start, current_end))
                current_start = current_end = line

        if current_start is not None:
            line_ranges.append((current_start, current_end))

        # Build aggregated entry
        total_matches = len(file_matches)

        if is_definition_file:
            # For definition file, just show summary
            aggregated.append(
                {
                    "file": file_path,
                    "is_definition": True,
                    "match_count": total_matches,
                    "line_ranges": [f"{s}-{e}" if s != e else str(s) for s, e in line_ranges],
                    "note": f"Class definition file ({total_matches} references, likely self-references)",
                }
            )
        else:
            # For usage files, show some sample lines
            sample_lines = []
            for match in file_matches[:max_lines_per_file]:
                sample_lines.append(
                    {
                        "line": match.get("line"),
                        "context": match.get("context", "").split("\n")[0][:100],
                    }
                )

            entry = {
                "file": file_path,
                "is_definition": False,
                "match_count": total_matches,
                "line_ranges": [f"{s}-{e}" if s != e else str(s) for s, e in line_ranges],
                "sample_lines": sample_lines,
            }
            if total_matches > max_lines_per_file:
                entry["truncated"] = True

            aggregated.append(entry)

    # Sort: definition file last, then by match count (descending)
    aggregated.sort(key=lambda x: (x.get("is_definition", False), -x.get("match_count", 0)))

    return aggregated


async def trace_reference_chain(
    start_asset: Annotated[
        str,
        "Starting asset path. Example: '/Game/BP_Player'",
    ],
    max_depth: Annotated[int, "Maximum depth to trace (default: 3, max: 10)."] = 3,
    direction: Annotated[
        Literal["outgoing", "incoming", "both"],
        "Direction: 'outgoing' | 'incoming' | 'both' (default).",
    ] = "both",
) -> dict:
    """Trace a cross-domain reference chain (UE plugin required)."""
    # Map unified direction names to UE plugin's expected values
    ue_direction = {
        "outgoing": "references",
        "incoming": "referencers",
        "both": "both",
    }.get(direction, "both")

    client = get_client()
    try:
        return await client.get_with_async(
            "/analysis/reference-chain",
            {"start": start_asset, "depth": max_depth, "direction": ue_direction},
            timeout_s=120.0,
        )
    except UEPluginError as e:
        return _ue_error("trace_reference_chain", e)


async def find_cpp_class_usage(
    cpp_class: Annotated[str, "C++ class name. Example: 'ULyraHealthSet'"],
    scope: Annotated[
        Literal["project", "engine", "all"],
        "C++ search scope: 'project' (default) | 'engine' | 'all'.",
    ] = "project",
    max_results: Annotated[int, "Max C++ matches to return (default: 200)."] = 200,
) -> dict:
    """Find usage of a C++ class across Blueprint/Asset and C++ code."""
    client = get_client()
    try:
        bp_result = await client.get("/analysis/cpp-class-usage", {"class": cpp_class})

        # Always include C++ references with aggregation
        try:
            from ..cpp_analyzer import get_analyzer

            analyzer = get_analyzer()
            cpp_result = await analyzer.find_references(cpp_class, scope=scope)
            raw_matches = cpp_result.get("matches", [])[:max_results]
            total_count = cpp_result.get("count", len(raw_matches))

            # Always aggregate by file
            aggregated = _aggregate_cpp_references(raw_matches, cpp_class)
            bp_result["cpp_references"] = aggregated
            bp_result["cpp_reference_count"] = total_count
            bp_result["cpp_files_with_references"] = len(aggregated)
            bp_result["cpp_reference_truncated"] = total_count > len(raw_matches)
        except Exception as e:
            bp_result["cpp_references"] = []
            bp_result["cpp_reference_count"] = 0
            bp_result["cpp_error"] = str(e)

        return bp_result
    except UEPluginError as e:
        return _ue_error("find_cpp_class_usage", e)
