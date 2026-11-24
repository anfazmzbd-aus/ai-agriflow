"""Intentional executor typing rejections checked by the diagnostic harness."""

from __future__ import annotations

from agentos.core import ExecutionResult
from agentos.workflows import (
    NodeId,
    SequentialWorkflowExecutor,
    WorkflowGraph,
    WorkflowNodeBinding,
    WorkflowNodeContext,
)


async def wrong_input(context: WorkflowNodeContext[str]) -> ExecutionResult[str]:
    """Reject a handler with a different input type."""
    return ExecutionResult[str].success(context.input_data)


async def raw(context: WorkflowNodeContext[int]) -> str:
    """Reject a raw output rather than an execution result."""
    return "raw"


def synchronous(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
    """Reject a nonawaitable handler result."""
    return ExecutionResult[int].success(context.input_data)


bad_input = WorkflowNodeBinding[int](NodeId("a"), wrong_input)  # reject: arg-type
bad_raw = WorkflowNodeBinding[int](NodeId("b"), raw)  # reject: arg-type
bad_sync = WorkflowNodeBinding[int](NodeId("c"), synchronous)  # reject: arg-type


async def invalid_operations(
    executor: SequentialWorkflowExecutor[int], binding: WorkflowNodeBinding[int]
) -> None:
    """Reject incorrect run input, snapshot writes, and unverified output narrowing."""
    binding.node_id = NodeId("replacement")  # reject: misc
    await executor.run("incorrect")  # reject: arg-type
    executor.results[NodeId("a")] = ExecutionResult[int].success(1)  # reject: index
    executor.results = {}  # reject: misc
    value: int = executor.results[NodeId("a")].value  # reject: assignment
    assert value == 1


def mismatched_binding(graph: WorkflowGraph, binding: WorkflowNodeBinding[str]) -> None:
    """Reject bindings with a different executor input type."""
    SequentialWorkflowExecutor[int](graph, [binding])  # reject: list-item
