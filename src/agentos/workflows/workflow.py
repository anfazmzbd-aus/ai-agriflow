from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from agentos.base.exceptions import WorkflowError


@dataclass(frozen=True, slots=True)
class WorkflowContext:
    """Mutable-by-replacement context passed between workflow steps."""

    state: Mapping[str, object] = field(default_factory=dict)

    def with_state(self, **updates: object) -> WorkflowContext:
        """Return a new context with additional state values."""
        return WorkflowContext(state={**self.state, **updates})


WorkflowStepHandler = Callable[[WorkflowContext], Awaitable[WorkflowContext]]


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """Named asynchronous workflow step."""

    name: str
    handler: WorkflowStepHandler


class SimpleWorkflow:
    """Sequential async workflow runner."""

    def __init__(self, name: str, steps: list[WorkflowStep]) -> None:
        """Create a workflow from an ordered list of steps."""
        if not steps:
            msg = "workflow requires at least one step"
            raise WorkflowError(msg)
        self.name = name
        self._steps = steps

    @property
    def steps(self) -> tuple[WorkflowStep, ...]:
        """Return workflow steps in execution order."""
        return tuple(self._steps)

    async def run(self, context: WorkflowContext | None = None) -> WorkflowContext:
        """Run every workflow step and return the final context."""
        current = context or WorkflowContext()
        for step in self._steps:
            current = await step.handler(current)
        return current
