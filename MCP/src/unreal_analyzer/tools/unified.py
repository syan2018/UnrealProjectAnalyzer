"""
Unified tools (minimal toolset).

Note on FastMCP exposure (per FastMCP docs):
- If `@mcp.tool(description=...)` is provided, the function docstring is ignored for the tool
  description shown to the client/LLM.
- Otherwise, the function docstring becomes the tool description.

Therefore:
- Keep tool `description=` and parameter annotations in English for LLM clarity.
- Human notes can live in normal comments or external docs (not in tool descriptions).
"""

from __future__ import annotations

from typing import Annotated, Literal

from ..cpp_analyzer import get_analyzer
from ..ue_client import get_client
from ..ue_client.http_client import UEPluginError

# Type aliases
ScopeType = Literal["project", "engine", "all"]
DomainType = Literal["cpp", "blueprint", "asset", "all"]


def _ue_error(tool: str, e: Exception) -> dict:
    """
    Build a structured UE-plugin connectivity error payload.

    Args:
        tool: Tool name.
        e: Exception.

    Returns:
        A dict with ok/error/detail/hint.
    """
    return {
        "ok": False,
        "error": f"UE Plugin API 调用失败（{tool}）",
        "detail": str(e),
        "hint": "请确认 UE 编辑器已启动且启用了 UnrealProjectAnalyzer 插件。",
    }


def _split_query_tokens(query: str) -> list[str]:
    """
    Split a user query into whitespace-separated tokens.

    Args:
        query: Raw query string.

    Returns:
        Token list (empty tokens removed).
    """
    return [t for t in query.strip().split() if t]


def _score_name_tokens(name: str, tokens: list[str]) -> int:
    """
    Score a name by how many tokens appear in it (case-insensitive).

    Args:
        name: Candidate name.
        tokens: Tokens to match.

    Returns:
        Integer score (higher is more relevant).
    """
    if not name or not tokens:
        return 0
    lower = name.lower()
    return sum(1 for t in tokens if t.lower() in lower)


async def search(
    query: Annotated[
        str,
        (
            "Search query. C++ uses smart matching, Blueprint/Asset uses wildcards.\n"
            "Examples: 'ULyraHealthComponent', 'GA_Weapon*', '*Damage*'"
        ),
    ],
    domain: Annotated[
        DomainType,
        (
            "Domain to search: 'cpp' | 'blueprint' | 'asset' | 'all' (default)."
        ),
    ] = "all",
    scope: Annotated[
        ScopeType,
        "Search scope: 'project' (default) | 'engine' | 'all'.",
    ] = "project",
    type_filter: Annotated[
        str,
        (
            "Type/class filter. For assets: 'Blueprint', 'Material', etc.\n"
            "For blueprints: parent class like 'GameplayAbility', 'Character'."
        ),
    ] = "",
    max_results: Annotated[int, "Max results per domain (default: 100)"] = 100,
) -> dict:
    """
    Unified search across C++, Blueprint, and Asset domains.

    Returns:
        A dict containing:
        - ok: bool
        - query: str
        - scope: str
        - domains_searched: list[str]
        - total_count: int
        - cpp_matches / blueprint_matches / asset_matches (if searched)
    """
    # Resolve domains to search
    if domain == "all":
        resolved_domains: list[Literal["cpp", "blueprint", "asset"]] = ["cpp", "blueprint", "asset"]
    elif domain in ("cpp", "blueprint", "asset"):
        resolved_domains = [domain]
    else:
        resolved_domains = ["cpp", "blueprint", "asset"]

    results = {
        "query": query,
        "scope": scope,
        "domains_searched": resolved_domains,
        "total_count": 0,
        "ok": True,
        "errors": [],
    }

    # C++ search
    if "cpp" in resolved_domains:
        try:
            analyzer = get_analyzer()
            cpp_result = await analyzer.search_code(
                query,
                "*.{h,cpp}",  # Default file pattern
                True,  # Always include comments
                scope=scope,
                max_results=max_results,
                query_mode="smart",  # Always smart mode
            )
            results["cpp_matches"] = cpp_result.get("matches", [])
            results["cpp_count"] = cpp_result.get("count", 0)
            results["cpp_truncated"] = cpp_result.get("truncated", False)
            results["total_count"] += results["cpp_count"]
        except Exception as e:
            results["cpp_matches"] = []
            results["cpp_count"] = 0
            results["cpp_error"] = str(e)
            results["ok"] = False
            results["errors"].append({"domain": "cpp", "error": str(e)})

    # Blueprint search (requires UE Plugin)
    if "blueprint" in resolved_domains:
        try:
            client = get_client()
            tokens = _split_query_tokens(query)
            patterns = tokens if tokens else [query]

            merged: dict[str, dict] = {}
            for pat in patterns:
                bp_result = await client.get(
                    "/blueprint/search",
                    {"pattern": pat, "class": type_filter},
                )
                for m in bp_result.get("matches", []):
                    path = str(m.get("path", ""))
                    if path:
                        merged[path] = m

            matches = list(merged.values())

            # Apply scope filter
            if scope == "project":
                matches = [m for m in matches if not m.get("path", "").startswith("/Script/")]
            elif scope == "engine":
                matches = [m for m in matches if m.get("path", "").startswith("/Script/")]

            # Score & sort for multi-token queries
            if len(patterns) > 1:
                for m in matches:
                    m["relevance_score"] = _score_name_tokens(str(m.get("name", "")), patterns)
                matches.sort(key=lambda x: int(x.get("relevance_score", 0)), reverse=True)

            results["blueprint_matches"] = matches[:max_results]
            results["blueprint_count"] = len(results["blueprint_matches"])
            results["total_count"] += results["blueprint_count"]
        except UEPluginError as e:
            results["blueprint_matches"] = []
            results["blueprint_count"] = 0
            results["blueprint_error"] = str(e)
            results["ok"] = False
            results["errors"].append({"domain": "blueprint", "error": str(e)})
        except Exception as e:
            results["blueprint_matches"] = []
            results["blueprint_count"] = 0
            results["blueprint_error"] = str(e)
            results["ok"] = False
            results["errors"].append({"domain": "blueprint", "error": str(e)})

    # Asset search (requires UE Plugin)
    if "asset" in resolved_domains:
        try:
            client = get_client()
            tokens = _split_query_tokens(query)
            patterns = tokens if tokens else [query]

            merged: dict[str, dict] = {}
            for pat in patterns:
                asset_result = await client.get(
                    "/asset/search",
                    {"pattern": pat, "type": type_filter},
                )
                for m in asset_result.get("matches", []):
                    path = str(m.get("path", ""))
                    if path:
                        merged[path] = m

            matches = list(merged.values())

            # Apply scope filter
            if scope == "project":
                matches = [
                    m for m in matches
                    if not m.get("path", "").startswith("/Script/")
                    and not m.get("path", "").startswith("/Engine/")
                ]
            elif scope == "engine":
                matches = [
                    m for m in matches
                    if m.get("path", "").startswith("/Script/")
                    or m.get("path", "").startswith("/Engine/")
                ]

            # Score & sort for multi-token queries
            if len(patterns) > 1:
                for m in matches:
                    m["relevance_score"] = _score_name_tokens(str(m.get("name", "")), patterns)
                matches.sort(key=lambda x: int(x.get("relevance_score", 0)), reverse=True)

            results["asset_matches"] = matches[:max_results]
            results["asset_count"] = len(results["asset_matches"])
            results["total_count"] += results["asset_count"]
        except UEPluginError as e:
            results["asset_matches"] = []
            results["asset_count"] = 0
            results["asset_error"] = str(e)
            results["ok"] = False
            results["errors"].append({"domain": "asset", "error": str(e)})
        except Exception as e:
            results["asset_matches"] = []
            results["asset_count"] = 0
            results["asset_error"] = str(e)
            results["ok"] = False
            results["errors"].append({"domain": "asset", "error": str(e)})

    return results


async def get_hierarchy(
    name: Annotated[
        str,
        (
            "C++ class name OR Blueprint asset path.\n"
            "Examples: 'ULyraHealthComponent', '/Game/BP_Hero'"
        ),
    ],
    domain: Annotated[
        Literal["cpp", "blueprint"],
        "Hierarchy domain: 'cpp' (default) | 'blueprint'.",
    ] = "cpp",
    scope: Annotated[
        ScopeType,
        "C++ search scope: 'project' (default) | 'engine' | 'all'.",
    ] = "project",
) -> dict:
    """Get inheritance hierarchy for a class (C++ or Blueprint)."""
    if domain == "cpp":
        analyzer = get_analyzer()
        return await analyzer.find_class_hierarchy(name, True, scope=scope)  # Always include interfaces
    else:
        try:
            client = get_client()
            return await client.get("/blueprint/hierarchy", {"bp_path": name})
        except UEPluginError as e:
            return _ue_error("get_hierarchy", e)


async def get_references(
    path: Annotated[
        str,
        (
            "Identifier or asset path.\n"
            "Examples: 'ULyraHealthComponent', '/Game/BP_Player'"
        ),
    ],
    domain: Annotated[
        Literal["cpp", "blueprint", "asset"],
        "Reference domain: 'cpp' | 'blueprint' | 'asset' (default).",
    ] = "asset",
    scope: Annotated[
        ScopeType,
        "C++ search scope: 'project' (default) | 'engine' | 'all'.",
    ] = "project",
    direction: Annotated[
        Literal["outgoing", "incoming", "both"],
        "Direction: 'outgoing' | 'incoming' | 'both' (default).",
    ] = "both",
) -> dict:
    """
    Get references for an item (outgoing/incoming/both).
    """
    results = {
        "path": path,
        "domain": domain,
        "direction": direction,
    }

    if domain == "cpp":
        # For C++, use identifier search
        analyzer = get_analyzer()
        if direction in ("incoming", "both"):
            refs = await analyzer.find_references(path, scope=scope)
            results["references"] = refs.get("matches", [])
            results["reference_count"] = refs.get("count", 0)
        results["ok"] = True
        return results

    # Blueprint/Asset use UE Plugin
    try:
        client = get_client()
        param_key = "bp_path" if domain == "blueprint" else "asset_path"

        if direction in ("outgoing", "both"):
            endpoint = f"/{domain}/references" if domain == "asset" else f"/{domain}/dependencies"
            out_result = await client.get(endpoint, {param_key: path})
            results["outgoing"] = out_result.get("dependencies", out_result.get("references", []))

        if direction in ("incoming", "both"):
            in_result = await client.get(f"/{domain}/referencers", {param_key: path})
            results["incoming"] = in_result.get("referencers", [])

        results["ok"] = True
        return results
    except UEPluginError as e:
        return _ue_error("get_references", e)


async def get_details(
    path: Annotated[
        str,
        (
            "C++ class/file OR Blueprint/Asset path.\n"
            "Examples: 'ULyraHealthComponent', '/Game/BP_Player'"
        ),
    ],
    domain: Annotated[
        Literal["cpp", "blueprint", "asset"],
        "Details domain: 'cpp' | 'blueprint' (default) | 'asset'.",
    ] = "blueprint",
    scope: Annotated[
        ScopeType,
        "C++ search scope: 'project' (default) | 'engine' | 'all'.",
    ] = "project",
) -> dict:
    """
    Get detailed information about an item.
    """
    if domain == "cpp":
        analyzer = get_analyzer()

        # If user passed a file path, return file-oriented analysis instead of "Class not found".
        lowered = path.lower().strip()
        if lowered.endswith((".h", ".hpp", ".cpp", ".cc", ".cxx")):
            try:
                return {
                    "type": "cpp_file",
                    "ok": True,
                    "result": await analyzer.analyze_file(path),
                }
            except Exception as e:
                return {
                    "ok": False,
                    "error_code": "cpp_file_analyze_failed",
                    "detail": str(e),
                    "suggestions": [
                        "Check that the file exists and is readable.",
                        (
                            "If you meant a class name, pass it as "
                            "get_details(path='ULyraHealthComponent', domain='cpp')."
                        ),
                    ],
                }

        # Otherwise treat as a class name.
        try:
            return await analyzer.analyze_class(path, scope=scope)
        except Exception as e:
            return {
                "ok": False,
                "error_code": "cpp_class_not_found",
                "detail": str(e),
                "suggestions": [
                    "If you passed a file path, set domain='cpp' and pass a .h/.cpp path.",
                    (
                        "Try search(query='LyraHealthComponent', domain='cpp', scope='project') "
                        "to find candidates."
                    ),
                ],
            }

    try:
        client = get_client()
        if domain == "blueprint":
            return await client.get("/blueprint/details", {"bp_path": path})
        else:  # asset
            return await client.get("/asset/metadata", {"asset_path": path})
    except UEPluginError as e:
        return _ue_error("get_details", e)
