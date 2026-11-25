"""Run a deterministic local DAG through managed Runtime lifecycle without external services."""

from __future__ import annotations

import asyncio

from agentos.core import ExecutionResult
from agentos.runtime import Runtime
from agentos.workflows import (
    NodeId,
    SequentialWorkflowExecutor,
    WorkflowGraph,
    WorkflowNodeBinding,
    WorkflowNodeContext,
    WorkflowNodeSpec,
)

COLLECT, REPORT = NodeId("collect"), NodeId("report")


async def collect(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
    """Produce deterministic reference data."""
    return ExecutionResult[int].success(context.input_data * 2)


async def report(context: WorkflowNodeContext[int]) -> ExecutionResult[str]:
    """Validate the dependency value before producing a report."""
    dependency = context.dependency_result(COLLECT)
    value = dependency.value
    if not dependency.has_value or not isinstance(value, int):
        return ExecutionResult[str].failure("expected integer reference data")
    return ExecutionResult[str].success(f"reference result: {value}")


async def main() -> None:
    """Execute the demo and print its final value."""
    graph = WorkflowGraph((WorkflowNodeSpec(REPORT, (COLLECT,)), WorkflowNodeSpec(COLLECT)))
    executor = SequentialWorkflowExecutor(
        graph,
        [
            WorkflowNodeBinding[int](COLLECT, collect),
            WorkflowNodeBinding[int](REPORT, report),
        ],
    )
    runtime = Runtime.from_settings()
    await runtime.initialize_async()
    await runtime.start_async()
    try:
        # Await completion (including exception/cancellation cleanup) before stop.
        outcome = await runtime.run_workflow(executor, 7)
        if outcome.value is not None:
            print(outcome.value[REPORT].value)
    finally:
        await runtime.stop_async()


if __name__ == "__main__":
    asyncio.run(main())
