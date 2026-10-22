from __future__ import annotations

from collections.abc import Mapping

from agentos.tools import FunctionTool, ToolResult, ToolSpec


async def test_function_tool_invokes_handler() -> None:
    """FunctionTool should call its async handler."""
    async def handler(arguments: Mapping[str, object]) -> ToolResult:
        return ToolResult(value=arguments["name"])

    tool = FunctionTool(
        spec=ToolSpec(name="greeter", description="Return the provided name."),
        _handler=handler,
    )

    result = await tool.invoke({"name": "AgriFlow"})

    assert tool.name == "greeter"
    assert result.value == "AgriFlow"
