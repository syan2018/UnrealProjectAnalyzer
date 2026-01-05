"""
MCP Server entry point.

Provides unified access to:
- Blueprint analysis tools (via UE5 Plugin HTTP API)
- Asset reference tools (via UE5 Plugin HTTP API)
- C++ source analysis tools (built-in tree-sitter based)
"""

import asyncio
from fastmcp import FastMCP

from .config import Config
from .tools import blueprint, asset, cpp, cross_domain

# Initialize MCP server
mcp = FastMCP(
    name="UE5ProjectAnalyzer",
    version="0.1.0",
)


def register_tools():
    """Register all MCP tools."""
    # Blueprint tools
    mcp.tool()(blueprint.search_blueprints)
    mcp.tool()(blueprint.get_blueprint_hierarchy)
    mcp.tool()(blueprint.get_blueprint_dependencies)
    mcp.tool()(blueprint.get_blueprint_referencers)
    mcp.tool()(blueprint.get_blueprint_graph)
    mcp.tool()(blueprint.get_blueprint_details)
    
    # Asset tools
    mcp.tool()(asset.search_assets)
    mcp.tool()(asset.get_asset_references)
    mcp.tool()(asset.get_asset_referencers)
    mcp.tool()(asset.get_asset_metadata)
    
    # C++ analysis tools
    mcp.tool()(cpp.analyze_cpp_class)
    mcp.tool()(cpp.get_cpp_class_hierarchy)
    mcp.tool()(cpp.search_cpp_code)
    mcp.tool()(cpp.find_cpp_references)
    mcp.tool()(cpp.detect_ue_patterns)
    mcp.tool()(cpp.get_cpp_blueprint_exposure)
    
    # Cross-domain tools
    mcp.tool()(cross_domain.trace_reference_chain)
    mcp.tool()(cross_domain.find_cpp_class_usage)


def main():
    """Run the MCP server."""
    register_tools()
    mcp.run()


if __name__ == "__main__":
    main()
