from __future__ import annotations

from agentos.adapters import LangGraphAdapter
from agentos.workflows import SimpleWorkflow, WorkflowContext, WorkflowStep


async def noop(context: WorkflowContext) -> WorkflowContext:
    """Return the workflow context unchanged."""
    return context


def test_langgraph_adapter_describes_workflow() -> None:
    """LangGraphAdapter should expose graph-ready metadata."""
    workflow = SimpleWorkflow(name="demo", steps=[WorkflowStep("noop", noop)])

    description = LangGraphAdapter(workflow).describe()

    assert description == {"engine": "langgraph", "workflow": "demo", "steps": ["noop"]}
