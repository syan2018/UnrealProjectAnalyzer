"""
MCP Server entry point.

Provides unified access to:
- Blueprint analysis tools (via Unreal Plugin HTTP API)
- Asset reference tools (via Unreal Plugin HTTP API)
- C++ source analysis tools (built-in tree-sitter based)
- Cross-domain analysis tools

This server enables AI agents to comprehensively analyze Unreal projects,
tracing references across Blueprint ↔ C++ ↔ Asset boundaries.

Configuration (via environment variables):
- CPP_SOURCE_PATH: Path to project's C++ source directory (required for C++ analysis)
- UNREAL_ENGINE_PATH: Path to Unreal installation (optional, for engine source analysis)
- UE_PLUGIN_HOST: Host for Unreal Plugin HTTP API (default: localhost)
- UE_PLUGIN_PORT: Port for Unreal Plugin HTTP API (default: 8080)
"""

from __future__ import annotations

import argparse
import os
import sys
from fastmcp import FastMCP

from .config import get_config
from .tools import blueprint, asset, cpp, cross_domain

# Initialize MCP server
mcp = FastMCP(
    name="UnrealProjectAnalyzer",
    version="0.1.0",
)


def _is_ue_plugin_available() -> bool:
    """
    Check if Unreal Plugin HTTP API is configured.
    
    Returns True if UE_PLUGIN_HOST is explicitly set (not default 'localhost').
    This helps distinguish between:
    - Running with UE Editor (plugin available)
    - Running standalone for C++ analysis only
    """
    host = os.getenv("UE_PLUGIN_HOST")
    # Consider available if explicitly set to any value
    return host is not None and host.strip() != ""


def register_tools():
    """
    Register all MCP tools.
    
    Tools are organized into groups focused on reference chain tracing:
    - Blueprint: Blueprint analysis via Unreal Plugin (requires UE Editor)
    - Asset: Asset reference tracking via Unreal Plugin (requires UE Editor)
    - C++: Source code analysis via tree-sitter (always available)
    - Cross-domain: Reference tracing across all domains (requires UE Editor)
    
    If UE_PLUGIN_HOST is not configured, Blueprint/Asset/Cross-domain tools
    will be disabled and only C++ analysis will be available.
    """
    
    ue_available = _is_ue_plugin_available()
    
    if not ue_available:
        print("[Unreal Analyzer] Warning: UE_PLUGIN_HOST not configured.")
        print("  Blueprint, Asset, and Cross-domain tools are DISABLED.")
        print("  Only C++ source analysis tools are available.")
        print("  To enable all tools, set --ue-plugin-host or UE_PLUGIN_HOST env var.")
        print("")
    
    # ========================================================================
    # Blueprint Tools (require Unreal Plugin)
    # ========================================================================
    if ue_available:
        mcp.tool(
            description="Search blueprints by name pattern and optional class filter"
        )(blueprint.search_blueprints)
        
        mcp.tool(
            description="Get the inheritance hierarchy of a blueprint"
        )(blueprint.get_blueprint_hierarchy)
        
        mcp.tool(
            description="Get all dependencies (referenced assets/classes) of a blueprint"
        )(blueprint.get_blueprint_dependencies)
        
        mcp.tool(
            description="Get all assets/blueprints that reference this blueprint"
        )(blueprint.get_blueprint_referencers)
        
        mcp.tool(
            description="Get the node graph of a blueprint function or event graph"
        )(blueprint.get_blueprint_graph)
        
        mcp.tool(
            description="Get comprehensive details about a blueprint (variables, functions, components)"
        )(blueprint.get_blueprint_details)
    
    # ========================================================================
    # Asset Tools (require Unreal Plugin)
    # ========================================================================
    if ue_available:
        mcp.tool(
            description="Search assets by name pattern and optional type filter"
        )(asset.search_assets)
        
        mcp.tool(
            description="Get all assets that this asset references"
        )(asset.get_asset_references)
        
        mcp.tool(
            description="Get all assets that reference this asset"
        )(asset.get_asset_referencers)
        
        mcp.tool(
            description="Get metadata information about an asset"
        )(asset.get_asset_metadata)
    
    # ========================================================================
    # C++ Analysis Tools (always available)
    # ========================================================================
    # These use tree-sitter for local source analysis
    # All focused on understanding C++ ↔ Blueprint boundaries
    
    mcp.tool(
        description="Analyze a C++ class structure (methods, properties, inheritance)"
    )(cpp.analyze_cpp_class)
    
    mcp.tool(
        description="Get the complete inheritance hierarchy of a C++ class"
    )(cpp.get_cpp_class_hierarchy)
    
    mcp.tool(
        description="Search through C++ source code with regex support"
    )(cpp.search_cpp_code)
    
    mcp.tool(
        description="Find all references to a C++ identifier (class, function, variable)"
    )(cpp.find_cpp_references)
    
    mcp.tool(
        description="Detect UE patterns (UPROPERTY, UFUNCTION, UCLASS) that expose to Blueprints"
    )(cpp.detect_ue_patterns)
    
    mcp.tool(
        description="Get all Blueprint-exposed API from a C++ header file"
    )(cpp.get_cpp_blueprint_exposure)
    
    # ========================================================================
    # Cross-Domain Tools (require Unreal Plugin)
    # ========================================================================
    if ue_available:
        mcp.tool(
            description="Trace a complete reference chain across Blueprint/Asset/C++ boundaries"
        )(cross_domain.trace_reference_chain)
        
        mcp.tool(
            description="Find all Blueprints and Assets that use a specific C++ class"
        )(cross_domain.find_cpp_class_usage)
    
    # Print summary
    if ue_available:
        print("[Unreal Analyzer] All tools registered (Blueprint + Asset + C++ + Cross-domain)")
    else:
        print("[Unreal Analyzer] C++ analysis tools registered (6 tools)")


def initialize_from_environment():
    """
    Initialize analyzer from environment variables.
    
    Environment variables:
    - CPP_SOURCE_PATH: Path to project's C++ source directory
    - UNREAL_ENGINE_PATH: Path to Unreal installation
    """
    from .cpp_analyzer import get_analyzer
    import asyncio
    
    cpp_source_path = os.getenv("CPP_SOURCE_PATH")
    unreal_engine_path = os.getenv("UNREAL_ENGINE_PATH")
    
    # Also check config
    config = get_config()
    
    analyzer = get_analyzer()
    
    async def init():
        # Priority: CPP_SOURCE_PATH > UNREAL_ENGINE_PATH
        if cpp_source_path:
            try:
                await analyzer.initialize_custom_codebase(cpp_source_path)
                print(f"[Unreal Analyzer] Initialized with C++ source path: {cpp_source_path}")
                return True
            except Exception as e:
                print(f"[Unreal Analyzer] Failed to initialize from CPP_SOURCE_PATH: {e}")
        
        if unreal_engine_path:
            try:
                await analyzer.initialize(unreal_engine_path)
                print(f"[Unreal Analyzer] Initialized with UE path: {unreal_engine_path}")
                return True
            except Exception as e:
                print(f"[Unreal Analyzer] Failed to initialize from UNREAL_ENGINE_PATH: {e}")
        
        print("[Unreal Analyzer] Warning: No C++ source path configured.")
        print("  Set CPP_SOURCE_PATH environment variable to enable C++ analysis.")
        return False
    
    # Run initialization
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If there's already a running loop, create a task
            asyncio.create_task(init())
        else:
            loop.run_until_complete(init())
    except RuntimeError:
        # No event loop exists, create one
        asyncio.run(init())


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unreal-analyzer",
        description="Unreal Project Analyzer MCP Server (FastMCP)",
    )

    parser.add_argument(
        "--cpp-source-path",
        help="项目 C++ 源码根目录（等价 CPP_SOURCE_PATH，优先级高于环境变量）",
        default=None,
    )
    parser.add_argument(
        "--unreal-engine-path",
        help="UE 安装目录（等价 UNREAL_ENGINE_PATH，可选）",
        default=None,
    )
    parser.add_argument(
        "--ue-plugin-host",
        help="UE 插件 HTTP API Host（等价 UE_PLUGIN_HOST）",
        default=None,
    )
    parser.add_argument(
        "--ue-plugin-port",
        type=int,
        help="UE 插件 HTTP API Port（等价 UE_PLUGIN_PORT）",
        default=None,
    )
    parser.add_argument(
        "--no-init",
        action="store_true",
        help="不进行启动时初始化（跳过 initialize_from_environment）",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="打印最终配置并退出（用于排查环境变量/参数覆盖）",
    )

    # --------------------------------------------------------------------
    # FastMCP transport options
    #
    # Background:
    # - Cursor MCP integration commonly uses stdio (default)
    # - For "quick connect" from other clients, FastMCP supports HTTP/SSE
    # - We keep stdio as default, and optionally allow http/sse
    # --------------------------------------------------------------------
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="MCP 传输方式：stdio（默认，适配 Cursor）/ http（Streamable HTTP）/ sse",
    )
    parser.add_argument(
        "--mcp-host",
        default="127.0.0.1",
        help="当 transport=http/sse 时，HTTP 服务监听 Host（默认 127.0.0.1）",
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=8000,
        help="当 transport=http/sse 时，HTTP 服务监听 Port（默认 8000）",
    )
    parser.add_argument(
        "--mcp-path",
        default="/mcp",
        help="当 transport=http 时，HTTP 路由前缀 Path（默认 /mcp）",
    )

    return parser


def _apply_cli_overrides(args: argparse.Namespace) -> None:
    """
    Apply CLI arguments by overriding environment variables.

    Design choice:
    - Config / analyzer initialization in this project is env-driven
    - CLI args should override env for a single-run convenience
    """
    if args.cpp_source_path:
        os.environ["CPP_SOURCE_PATH"] = args.cpp_source_path
    if args.unreal_engine_path:
        os.environ["UNREAL_ENGINE_PATH"] = args.unreal_engine_path
    if args.ue_plugin_host:
        os.environ["UE_PLUGIN_HOST"] = args.ue_plugin_host
    if args.ue_plugin_port is not None:
        os.environ["UE_PLUGIN_PORT"] = str(args.ue_plugin_port)


def main():
    """Run the MCP server."""
    parser = _build_arg_parser()
    args = parser.parse_args(sys.argv[1:])
    _apply_cli_overrides(args)

    if args.print_config:
        cfg = get_config()
        print("[Unreal Analyzer] Effective config:")
        print("  CPP_SOURCE_PATH:", os.getenv("CPP_SOURCE_PATH"))
        print("  UNREAL_ENGINE_PATH:", os.getenv("UNREAL_ENGINE_PATH"))
        print("  UE_PLUGIN_URL:", cfg.ue_plugin_url)
        print("  cpp_source_paths:", cfg.cpp_source_paths)
        return

    register_tools()
    
    # Initialize from environment
    if not args.no_init:
        try:
            initialize_from_environment()
        except Exception as e:
            print(f"[Unreal Analyzer] Initialization error: {e}")

    # Run server with selected transport.
    #
    # NOTE:
    # - stdio is the default and is the common choice for Cursor MCP.
    # - http/sse is helpful when you want to host the MCP server as a local web service
    #   (e.g. when launched from UE Editor with a "Start MCP" button).
    if args.transport == "stdio":
        mcp.run()
        return

    if args.transport == "http":
        mcp.run(transport="http", host=args.mcp_host, port=args.mcp_port, path=args.mcp_path)
        return

    # sse
    mcp.run(transport="sse", host=args.mcp_host, port=args.mcp_port)


if __name__ == "__main__":
    main()
