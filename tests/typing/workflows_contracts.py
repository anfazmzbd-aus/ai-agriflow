"""Positive static contracts; checked explicitly with MyPy."""

from __future__ import annotations

from typing import assert_type

from agentos.core import ExecutionResult
from agentos.workflows import (
    NodeId,
    WorkflowGraph,
    WorkflowNodeContext,
    WorkflowNodeHandler,
    WorkflowNodeSpec,
    WorkflowRunState,
)


async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[str]:
    """Preserve concrete input and output types."""
    assert_type(context.input_data, int)
    return ExecutionResult[str].success(str(context.input_data))


async def none_handler(context: WorkflowNodeContext[int]) -> ExecutionResult[None]:
    """Return a legitimate None value."""
    return ExecutionResult[None].success(None)


typed: WorkflowNodeHandler[int, str] = handler
typed_none: WorkflowNodeHandler[int, None] = none_handler


def check_state() -> None:
    """Heterogeneous storage exposes object rather than unchecked typed values."""
    root = NodeId("root")
    leaf = NodeId("leaf")
    run = WorkflowRunState(
        WorkflowGraph((WorkflowNodeSpec(root), WorkflowNodeSpec(leaf, (root,)))),
        input_data=3,
    )
    run.record_result(root, ExecutionResult[int].success(4))
    run.record_result(leaf, ExecutionResult[str].success("different"))
    assert_type(run.context_for(root), WorkflowNodeContext[int])
    assert_type(run.result_for(root), ExecutionResult[object])
    assert_type(run.result_for(root).value, object)
    assert_type(run.context_for(leaf).dependency_result(root), ExecutionResult[object])
