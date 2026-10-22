from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Input context provided to an agent invocation."""

    goal: str
    data: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentResult:
    """Structured result produced by an agent."""

    content: str
    metadata: Mapping[str, object] = field(default_factory=dict)


class Agent(Protocol):
    """Protocol implemented by AgentOS-compatible agents."""

    @property
    def name(self) -> str:
        """Return the stable agent name."""

    async def run(self, context: AgentContext) -> AgentResult:
        """Run the agent for the provided context."""


@dataclass(frozen=True, slots=True)
class EchoAgent:
    """Deterministic agent useful for examples and tests."""

    name: str = "echo"

    async def run(self, context: AgentContext) -> AgentResult:
        """Return the requested goal as agent output."""
        return AgentResult(content=context.goal, metadata={"agent": self.name})
