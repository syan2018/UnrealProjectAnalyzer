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

from ..config import get_config
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
            "Search query. For C++: default query_mode='smart' splits on whitespace into tokens, "
            "or treats it as regex if it looks like a regex. "
            "For Blueprint/Asset: treated as a wildcard name pattern."
        ),
    ],
    domain: Annotated[
        DomainType,
        (
            "Domain to search: 'cpp' | 'blueprint' | 'asset' | 'all'. "
            "Ignored if 'domains' is provided."
        ),
    ] = "all",
    domains: Annotated[
        list[Literal["cpp", "blueprint", "asset"]] | None,
        "Optional explicit list of domains. If provided, overrides 'domain'.",
    ] = None,
    scope: Annotated[
        ScopeType,
        (
            "Search scope for C++ and for filtering UE assets: "
            "'project' (default) | 'engine' | 'all'."
        ),
    ] = "project",
    file_pattern: Annotated[str, "C++ file glob pattern (e.g. '*.{h,cpp}')"] = "*.{h,cpp}",
    asset_type: Annotated[str, "Asset class filter (UE asset search only)"] = "",
    class_filter: Annotated[str, "Blueprint parent class filter (Blueprint search only)"] = "",
    max_results: Annotated[int, "Max results per domain"] = 100,
    include_comments: Annotated[bool, "Include comment lines in C++ search"] = True,
    query_mode: Annotated[
        Literal["smart", "regex", "tokens"],
        "C++ query mode: 'smart' (default) | 'regex' | 'tokens'.",
    ] = "smart",
) -> dict:
    """
    Unified search across C++, Blueprint, and Asset domains.

    Returns a consistent result shape with per-domain matches + counts, plus
    warnings/tips to reduce confusion in common misconfiguration cases.

    Returns:
        A dict containing:
        - ok: bool
        - query: str
        - scope: str
        - domains_searched: list[str]
        - total_count: int
        - errors: list[dict]
        - warnings: list[str]
        - tips: list[str]
        - config_summary: dict (best-effort)
        - cpp_matches / blueprint_matches / asset_matches (if searched)
    """
    # Resolve domains to search.
    resolved_domains: list[Literal["cpp", "blueprint", "asset"]] = []
    if domains is not None:
        resolved_domains = [d for d in domains if d in ("cpp", "blueprint", "asset")]
    else:
        if domain == "all":
            resolved_domains = ["cpp", "blueprint", "asset"]
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
        "warnings": [],
        "tips": [],
        "query_mode": query_mode,
    }

    # Add config transparency to reduce confusion about what "project" means in practice.
    try:
        cfg = get_config()
        results["config_summary"] = {
            "cpp_project_paths": cfg.get_project_paths(),
            "cpp_engine_paths": cfg.get_engine_paths(),
            "default_scope": str(cfg.default_scope),
        }
        # Warn if project path looks like a plugin directory (common misconfig).
        for p in cfg.get_project_paths():
            if "plugins" in p.lower() and "unrealprojectanalyzer" in p.lower():
                results["warnings"].append(
                    "CPP_SOURCE_PATH seems to point to a plugin folder. "
                    "Recommended: set it to <Project>/Source."
                )
                break
    except Exception:
        pass

    # C++ search
    if "cpp" in resolved_domains:
        try:
            analyzer = get_analyzer()
            cpp_result = await analyzer.search_code(
                query,
                file_pattern,
                include_comments,
                scope=scope,
                max_results=max_results,
                query_mode=query_mode,
            )
            results["cpp_matches"] = cpp_result.get("matches", [])
            results["cpp_count"] = cpp_result.get("count", 0)
            results["cpp_truncated"] = cpp_result.get("truncated", False)
            results["cpp_searched_paths"] = cpp_result.get("searched_paths", [])
            results["cpp_query_mode_resolved"] = cpp_result.get("query_mode_resolved")
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
            # UE endpoint is name-wildcard based; multi-word queries should be tokenized.
            patterns = tokens if tokens else [query]

            merged: dict[str, dict] = {}
            for pat in patterns:
                bp_result = await client.get(
                    "/blueprint/search",
                    {
                        "pattern": pat,
                        "class": class_filter,
                    },
                )
                for m in bp_result.get("matches", []):
                    path = str(m.get("path", ""))
                    if not path:
                        continue
                    merged[path] = m

            matches = list(merged.values())

            # Apply scope filter (exclude engine paths for project scope)
            if scope == "project":
                matches = [m for m in matches if not m.get("path", "").startswith("/Script/")]
            elif scope == "engine":
                matches = [m for m in matches if m.get("path", "").startswith("/Script/")]

            # Score & sort for multi-token queries.
            if len(patterns) > 1:
                for m in matches:
                    m["relevance_score"] = _score_name_tokens(str(m.get("name", "")), patterns)
                matches.sort(key=lambda x: int(x.get("relevance_score", 0)), reverse=True)

            # Limit results
            if len(matches) > max_results:
                matches = matches[:max_results]
                results["blueprint_truncated"] = True
            else:
                results["blueprint_truncated"] = False

            results["blueprint_matches"] = matches
            results["blueprint_count"] = len(matches)
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
            results["blueprint_error"] = f"Unexpected error: {e}"
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
                    {
                        "pattern": pat,
                        "type": asset_type,
                    },
                )
                for m in asset_result.get("matches", []):
                    path = str(m.get("path", ""))
                    if not path:
                        continue
                    merged[path] = m

            matches = list(merged.values())

            # Apply scope filter
            if scope == "project":
                matches = [
                    m
                    for m in matches
                    if not m.get("path", "").startswith("/Script/")
                    and not m.get("path", "").startswith("/Engine/")
                ]
            elif scope == "engine":
                matches = [
                    m
                    for m in matches
                    if m.get("path", "").startswith("/Script/")
                    or m.get("path", "").startswith("/Engine/")
                ]

            # Score & sort for multi-token queries.
            if len(patterns) > 1:
                for m in matches:
                    m["relevance_score"] = _score_name_tokens(str(m.get("name", "")), patterns)
                matches.sort(key=lambda x: int(x.get("relevance_score", 0)), reverse=True)

            # Limit results
            if len(matches) > max_results:
                matches = matches[:max_results]
                results["asset_truncated"] = True
            else:
                results["asset_truncated"] = False

            results["asset_matches"] = matches
            results["asset_count"] = len(matches)
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
            results["asset_error"] = f"Unexpected error: {e}"
            results["ok"] = False
            results["errors"].append({"domain": "asset", "error": str(e)})

    # Add tips when nothing found.
    if results.get("total_count", 0) == 0:
        if (
            "cpp" in resolved_domains
            and query_mode in ("smart", "tokens")
            and any(ch.isspace() for ch in query)
        ):
            results["tips"].append(
                "C++ 搜索默认按空格分词并按命中度排序；建议先用更少关键词，"
                "如：LyraGameplayAbility / Damage / Execution"
            )
        if "blueprint" in resolved_domains or "asset" in resolved_domains:
            # Human-facing usage tips (Chinese is fine for end users).
            results["tips"].extend(
                [
                    "Blueprint/Asset search is name-based wildcard matching. Examples:",
                    "  - 'GA_*' finds GameplayAbilities with GA_ prefix",
                    "  - '*Weapon*' finds assets with 'Weapon' in name",
                    "  - '*Fire*' finds assets with 'Fire' in name",
                    f"Current query: {query!r}",
                    "Try: 'GA_*', '*Weapon*', '*Fire*'",
                ]
            )

    return results


async def get_hierarchy(
    name: Annotated[str, "C++ class name OR Blueprint path (e.g. '/Game/...')"],
    domain: Annotated[
        Literal["cpp", "blueprint"], "Hierarchy domain: 'cpp' or 'blueprint'"
    ] = "cpp",
    scope: Annotated[ScopeType, "C++ search scope: 'project' | 'engine' | 'all'"] = "project",
    include_interfaces: Annotated[bool, "Include implemented interfaces (C++ only)"] = True,
) -> dict:
    """
    Get inheritance hierarchy for a class (C++ or Blueprint).
    """
    if domain == "cpp":
        analyzer = get_analyzer()
        return await analyzer.find_class_hierarchy(name, include_interfaces, scope=scope)
    else:  # blueprint
        try:
            client = get_client()
            return await client.get("/blueprint/hierarchy", {"bp_path": name})
        except UEPluginError as e:
            return _ue_error("get_hierarchy", e)


async def get_references(
    path: Annotated[
        str, "Identifier or asset path (Blueprint/Asset: '/Game/...'; C++: identifier)"
    ],
    domain: Annotated[
        Literal["cpp", "blueprint", "asset"],
        "Reference domain: 'cpp' | 'blueprint' | 'asset'",
    ] = "asset",
    scope: Annotated[ScopeType, "C++ search scope: 'project' | 'engine' | 'all'"] = "project",
    direction: Annotated[
        Literal["outgoing", "incoming", "both"],
        "Direction: outgoing (references), incoming (referencers), both",
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
    path: Annotated[str, "C++ class name OR Blueprint/Asset path (e.g. '/Game/...')"],
    domain: Annotated[
        Literal["cpp", "blueprint", "asset"], "Details domain: 'cpp' | 'blueprint' | 'asset'"
    ] = "blueprint",
    scope: Annotated[ScopeType, "C++ search scope: 'project' | 'engine' | 'all'"] = "project",
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
