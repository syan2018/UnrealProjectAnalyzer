import asyncio

from fastmcp import FastMCP

from unreal_copilot.tools import skills


async def _find_tool(mcp: FastMCP, name: str):
    tools = await mcp.list_tools()
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"tool not found: {name}")


def test_run_unreal_skill_schema_keeps_optional_defaults():
    demo = FastMCP("demo")
    demo.add_tool(skills.run_unreal_skill)
    tool = asyncio.run(_find_tool(demo, "run_unreal_skill"))

    assert "required" not in tool.parameters
    for key in ["skill_name", "script", "args", "python"]:
        assert key in tool.parameters["properties"]
        assert tool.parameters["properties"][key]["default"] is None
