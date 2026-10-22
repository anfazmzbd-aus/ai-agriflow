from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Result returned by a tool invocation."""

    value: object
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Machine-readable description of an AgentOS tool."""

    name: str
    description: str


ToolCallable = Callable[[Mapping[str, object]], Awaitable[ToolResult]]


@dataclass(frozen=True, slots=True)
class FunctionTool:
    """Tool implementation backed by an asynchronous Python callable."""

    spec: ToolSpec
    _handler: ToolCallable

    @property
    def name(self) -> str:
        """Return the stable tool name."""
        return self.spec.name

    async def invoke(self, arguments: Mapping[str, object]) -> ToolResult:
        """Invoke the tool with validated argument data."""
        return await self._handler(arguments)
