from __future__ import annotations

import asyncio

from agentos.workflows import SimpleWorkflow, WorkflowContext, WorkflowStep


async def collect_context(context: WorkflowContext) -> WorkflowContext:
    """Collect input context for a workflow run."""
    return context.with_state(collected=True)


async def report_result(context: WorkflowContext) -> WorkflowContext:
    """Report a final workflow result."""
    return context.with_state(result="ready")


def main() -> None:
    """Run a minimal AgentOS workflow example."""
    workflow = SimpleWorkflow(
        name="simple",
        steps=[
            WorkflowStep("collect_context", collect_context),
            WorkflowStep("report_result", report_result),
        ],
    )
    result = asyncio.run(workflow.run())
    print(result.state["result"])


if __name__ == "__main__":
    main()
