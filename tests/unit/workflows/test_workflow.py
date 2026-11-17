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


async def test_linear_context_and_adapter_remain_compatible() -> None:
    """Legacy state replacement, input identity, and adapter descriptions remain intact."""
    from agentos.adapters import LangGraphAdapter

    state: dict[str, object] = {"original": True}
    context = WorkflowContext(state)
    assert context.state is state
    updated = context.with_state(extra=1)
    assert updated.state == {"original": True, "extra": 1}
    assert context.state == {"original": True}
    seen: list[WorkflowContext] = []

    async def handler(current: WorkflowContext) -> WorkflowContext:
        seen.append(current)
        return current.with_state(done=True)

    step = WorkflowStep("legacy", handler)
    workflow = SimpleWorkflow("legacy", [step])
    assert (await workflow.run(context)).state["done"] is True
    assert seen == [context]
    assert workflow.steps == (step,)
    assert LangGraphAdapter(workflow).describe() == {
        "engine": "langgraph",
        "workflow": "legacy",
        "steps": ["legacy"],
    }
