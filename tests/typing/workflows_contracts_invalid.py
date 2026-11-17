"""Intentional static errors; the runtime diagnostic test asserts every rejection."""

from __future__ import annotations

from agentos.core import ExecutionResult
from agentos.workflows import NodeId, WorkflowNodeContext, WorkflowNodeHandler, WorkflowRunState


def synchronous(context: WorkflowNodeContext[int]) -> ExecutionResult[str]:
    """Demonstrate rejection of synchronous handlers."""
    return ExecutionResult[str].success("value")


async def raw(context: WorkflowNodeContext[int]) -> str:
    """Raw values are not the result contract."""
    return "value"


async def wrong_input(context: WorkflowNodeContext[str]) -> ExecutionResult[str]:
    """Input contexts must match the declared input type."""
    return ExecutionResult[str].success(context.input_data)


async def wrong_output(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
    """Output values must match the declared output type."""
    return ExecutionResult[int].success(context.input_data)


bad_sync: WorkflowNodeHandler[int, str] = synchronous  # reject: assignment
bad_raw: WorkflowNodeHandler[int, str] = raw  # reject: assignment
bad_input: WorkflowNodeHandler[int, str] = wrong_input  # reject: assignment
bad_output: WorkflowNodeHandler[int, str] = wrong_output  # reject: assignment


def writes(context: WorkflowNodeContext[int], run: WorkflowRunState[int]) -> None:
    """Public snapshots, fields, and heterogeneous values cannot be retyped unsafely."""
    key = NodeId("root")
    context.dependency_results[key] = ExecutionResult[int].success(1)  # reject: index
    run.results[key] = ExecutionResult[int].success(1)  # reject: index
    context.input_data = 2  # reject: misc
    run.results = {}  # reject: misc
    value: int = run.result_for(key).value  # reject: assignment
    assert value == 1
