from __future__ import annotations

import pytest

from agentos.base import WorkflowError
from agentos.workflows import SimpleWorkflow, WorkflowContext, WorkflowStep


async def test_simple_workflow_runs_steps_in_order() -> None:
    """SimpleWorkflow should pass context through each step."""

    async def first(context: WorkflowContext) -> WorkflowContext:
        return context.with_state(first=True)

    async def second(context: WorkflowContext) -> WorkflowContext:
        return context.with_state(second=context.state["first"])

    workflow = SimpleWorkflow(
        name="ordered",
        steps=[WorkflowStep("first", first), WorkflowStep("second", second)],
    )

    result = await workflow.run()

    assert result.state == {"first": True, "second": True}


def test_simple_workflow_requires_steps() -> None:
    """SimpleWorkflow should reject empty workflows."""
    with pytest.raises(WorkflowError):
        SimpleWorkflow(name="empty", steps=[])
