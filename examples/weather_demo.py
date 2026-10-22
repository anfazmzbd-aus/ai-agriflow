from __future__ import annotations

import asyncio
from collections.abc import Mapping

from agentos.tools import FunctionTool, ToolResult, ToolSpec


async def weather_handler(arguments: Mapping[str, object]) -> ToolResult:
    """Return a deterministic crop-weather recommendation."""
    return ToolResult(
        value={"crop": "rice", "condition": "light rain", "action": "delay irrigation"},
        metadata={"source": "demo"},
    )


def main() -> None:
    """Run a deterministic weather demo placeholder."""
    tool = FunctionTool(
        spec=ToolSpec(name="weather_demo", description="Return deterministic weather advice."),
        _handler=weather_handler,
    )
    forecast = asyncio.run(tool.invoke({})).value
    if not isinstance(forecast, dict):
        raise TypeError("weather tool must return a dictionary")
    print(f"{forecast['crop']}: {forecast['condition']} — {forecast['action']}")


if __name__ == "__main__":
    main()
