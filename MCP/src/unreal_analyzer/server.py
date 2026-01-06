"""
MCP Server entry point - Unreal Project Analyzer.

Design goal: minimum toolset, maximum capability (minimum confusion).

Environment variables:
- CPP_SOURCE_PATH: Project C++ source root (recommended: <Project>/Source)
- UNREAL_ENGINE_PATH: Engine source root (optional)
- UE_PLUGIN_HOST: Unreal Editor plugin HTTP API host
- UE_PLUGIN_PORT: Unreal Editor plugin HTTP API port (default: 8080)
- DEFAULT_SEARCH_SCOPE: Default scope (project/engine/all)
"""

from __future__ import annotations

import argparse
import os
import sys

from fastmcp import FastMCP

from .config import get_config
from .tools import blueprint, cpp, cross_domain, unified

# Initialize MCP server
mcp = FastMCP(
    name="UnrealProjectAnalyzer",
    version="0.3.1",  # 用户反馈优化版本
)


def _is_ue_plugin_available() -> bool:
    """Check if the UE plugin HTTP API is configured."""
    host = os.getenv("UE_PLUGIN_HOST")
    return host is not None and host.strip() != ""


def register_tools():
    """
    Register MCP tools.

    Minimal toolset (8 total):

    Core tools (4):
    - search: Unified search (C++/Blueprint/Asset)
    - get_hierarchy: Inheritance hierarchy (C++ or Blueprint)
    - get_references: Reference relationships (incoming/outgoing/both)
    - get_details: Detailed info (C++/Blueprint/Asset)

    Specialized tools (4):
    - get_blueprint_graph: Blueprint graph (EventGraph/function graphs)
    - detect_ue_patterns: UE macro detection (format='detailed'|'summary')
    - trace_reference_chain: Cross-domain reference chain
    - find_cpp_class_usage: C++ class usage (Blueprint + C++)
    """

    ue_available = _is_ue_plugin_available()

    if not ue_available:
        print("[Unreal Analyzer] Warning: UE_PLUGIN_HOST is not configured.")
        print("  Blueprint/Asset tools are disabled; C++ analysis is still available.")
        print("  Set --ue-plugin-host or UE_PLUGIN_HOST to enable UE plugin features.")
        print("")

    # ========================================================================
    # 核心工具（统一接口）
    # ========================================================================
    mcp.tool(description="Unified search across C++/Blueprint/Asset (scope: project/engine/all)")(
        unified.search
    )

    mcp.tool(description="Get inheritance hierarchy (C++ or Blueprint)")(unified.get_hierarchy)

    mcp.tool(description="Get references (incoming/outgoing/both)")(unified.get_references)

    mcp.tool(description="Get details (C++/Blueprint/Asset)")(unified.get_details)

    # ========================================================================
    # 特殊工具（unified 无法完全覆盖的能力）
    # ========================================================================

    # 蓝图节点图 - 需要专门的图结构返回
    if ue_available:
        mcp.tool(description="Get Blueprint graph (EventGraph/function graphs)")(
            blueprint.get_blueprint_graph
        )

    # UE 模式检测 - 分析 UPROPERTY/UFUNCTION 等宏 (format='detailed'|'summary')
    mcp.tool(description="Detect UE macros (UPROPERTY/UFUNCTION/UCLASS) in a C++ file")(
        cpp.detect_ue_patterns
    )

    # 跨域引用链 - 需要递归追踪
    if ue_available:
        mcp.tool(description="Trace full reference chain (Blueprint/Asset)")(
            cross_domain.trace_reference_chain
        )

        mcp.tool(description="Find C++ class usage in Blueprint/Asset + C++ code")(
            cross_domain.find_cpp_class_usage
        )

    # 打印摘要
    tool_count = 4 + 1  # 核心工具 + C++ 特殊工具
    if ue_available:
        tool_count += 3  # 蓝图节点图 + 跨域工具
        print(f"[Unreal Analyzer] Registered {tool_count} tools (minimal toolset).")
    else:
        print(f"[Unreal Analyzer] Registered {tool_count} tools (C++-only mode).")


def initialize_from_environment():
    """Initialize analyzer from environment variables."""
    import asyncio

    from .cpp_analyzer import get_analyzer

    cpp_source_path = os.getenv("CPP_SOURCE_PATH")
    unreal_engine_path = os.getenv("UNREAL_ENGINE_PATH")

    analyzer = get_analyzer()

    async def init():
        if cpp_source_path:
            try:
                await analyzer.initialize_custom_codebase(cpp_source_path)
                print(f"[Unreal Analyzer] Project source path: {cpp_source_path}")
                if unreal_engine_path:
                    await analyzer.initialize(unreal_engine_path)
                    print(f"[Unreal Analyzer] Engine source path: {unreal_engine_path}")
                return True
            except Exception as e:
                print(f"[Unreal Analyzer] Failed to init project source path: {e}")

        if unreal_engine_path:
            try:
                await analyzer.initialize(unreal_engine_path)
                print(f"[Unreal Analyzer] Engine source path: {unreal_engine_path}")
                return True
            except Exception as e:
                print(f"[Unreal Analyzer] Failed to init engine source path: {e}")

        print("[Unreal Analyzer] Warning: no C++ source paths configured.")
        print("  Set CPP_SOURCE_PATH to enable project C++ analysis.")
        return False

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(init())
        else:
            loop.run_until_complete(init())
    except RuntimeError:
        asyncio.run(init())


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unreal-analyzer",
        description="Unreal Project Analyzer MCP Server",
    )

    parser.add_argument(
        "--cpp-source-path",
        help="Project C++ source root",
        default=None,
    )
    parser.add_argument(
        "--unreal-engine-path",
        help="Unreal Engine source root (optional)",
        default=None,
    )
    parser.add_argument(
        "--ue-plugin-host",
        help="UE plugin HTTP API host",
        default=None,
    )
    parser.add_argument(
        "--ue-plugin-port",
        type=int,
        help="UE plugin HTTP API port (default: 8080)",
        default=None,
    )
    parser.add_argument(
        "--default-scope",
        choices=["project", "engine", "all"],
        help="Default search scope",
        default=None,
    )
    parser.add_argument(
        "--no-init",
        action="store_true",
        help="Skip initialization on startup",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print effective config and exit",
    )

    # Transport 选项
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--mcp-host",
        default="127.0.0.1",
        help="Host for http/sse transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=8000,
        help="Port for http/sse transport (default: 8000)",
    )
    parser.add_argument(
        "--mcp-path",
        default="/mcp",
        help="Path prefix for http transport (default: /mcp)",
    )

    return parser


def _apply_cli_overrides(args: argparse.Namespace) -> None:
    """Apply CLI overrides to env vars (single-run convenience)."""
    if args.cpp_source_path:
        os.environ["CPP_SOURCE_PATH"] = args.cpp_source_path
    if args.unreal_engine_path:
        os.environ["UNREAL_ENGINE_PATH"] = args.unreal_engine_path
    if args.ue_plugin_host:
        os.environ["UE_PLUGIN_HOST"] = args.ue_plugin_host
    if args.ue_plugin_port is not None:
        os.environ["UE_PLUGIN_PORT"] = str(args.ue_plugin_port)
    if args.default_scope:
        os.environ["DEFAULT_SEARCH_SCOPE"] = args.default_scope


def main():
    """Run the MCP server."""
    parser = _build_arg_parser()
    args = parser.parse_args(sys.argv[1:])
    _apply_cli_overrides(args)

    if args.print_config:
        cfg = get_config()
        print("[Unreal Analyzer] Effective config:")
        print(f"  CPP_SOURCE_PATH: {os.getenv('CPP_SOURCE_PATH')}")
        print(f"  UNREAL_ENGINE_PATH: {os.getenv('UNREAL_ENGINE_PATH')}")
        print(f"  UE_PLUGIN_URL: {cfg.ue_plugin_url}")
        print(f"  DEFAULT_SCOPE: {cfg.default_scope}")
        print(f"  Project paths: {cfg.get_project_paths()}")
        print(f"  Engine paths: {cfg.get_engine_paths()}")
        return

    register_tools()

    if not args.no_init:
        try:
            initialize_from_environment()
        except Exception as e:
            print(f"[Unreal Analyzer] Initialization error: {e}")

    if args.transport == "stdio":
        mcp.run()
    elif args.transport == "http":
        mcp.run(transport="http", host=args.mcp_host, port=args.mcp_port, path=args.mcp_path)
    else:
        mcp.run(transport="sse", host=args.mcp_host, port=args.mcp_port)


if __name__ == "__main__":
    main()
