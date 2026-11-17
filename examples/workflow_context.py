"""Manually demonstrate DAG contexts and handlers without adding an executor."""

from __future__ import annotations

import asyncio

from agentos.core import ExecutionResult
from agentos.workflows import (
    NodeId,
    WorkflowGraph,
    WorkflowNodeContext,
    WorkflowNodeHandler,
    WorkflowNodeSpec,
    WorkflowRunState,
)

ROOT = NodeId("root")
REPORT = NodeId("report")


async def report(context: WorkflowNodeContext[str]) -> ExecutionResult[str]:
    """Narrow a heterogeneous dependency value before consuming it."""
    outcome = context.dependency_result(ROOT)
    value = outcome.value
    if not outcome.has_value or not isinstance(value, int):
        return ExecutionResult[str].failure("expected an integer dependency value")
    return ExecutionResult[str].success(f"{context.input_data}: {value}")


async def main() -> None:
    """Record one result and manually call a typed dependent handler."""
    graph = WorkflowGraph((WorkflowNodeSpec(ROOT), WorkflowNodeSpec(REPORT, (ROOT,))))
    run = WorkflowRunState(graph, input_data="reference")
    run.record_result(ROOT, ExecutionResult[int].success(7))
    handler: WorkflowNodeHandler[str, str] = report
    run.record_result(REPORT, await handler(run.context_for(REPORT)))
    print(run.result_for(REPORT).value)


if __name__ == "__main__":
    asyncio.run(main())
