"""Positive heterogeneous binding and executor typing contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from typing import assert_type

from agentos.core import ExecutionResult
from agentos.workflows import (
    NodeId,
    SequentialWorkflowExecutor,
    WorkflowGraph,
    WorkflowNodeBinding,
    WorkflowNodeContext,
    WorkflowNodeSpec,
)


async def integer(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
    """Return the input without widening the handler contract."""
    return ExecutionResult[int].success(context.input_data)


async def text(context: WorkflowNodeContext[int]) -> ExecutionResult[str]:
    """Return a different output type for the same typed run input."""
    return ExecutionResult[str].success(str(context.input_data))


async def none(context: WorkflowNodeContext[int]) -> ExecutionResult[None]:
    """Keep successful None output valid."""
    return ExecutionResult[None].success(None)


def factory(context: WorkflowNodeContext[int]) -> Awaitable[ExecutionResult[int]]:
    """Accept a synchronous factory that returns an awaitable."""
    return integer(context)


class CallableHandler:
    """Accept callable objects with a typed asynchronous call method."""

    async def __call__(self, context: WorkflowNodeContext[int]) -> ExecutionResult[str]:
        """Return a concrete result."""
        return await text(context)


async def check() -> None:
    """Bind heterogeneous output types without caller casts or Any."""
    a, b, c = NodeId("a"), NodeId("b"), NodeId("c")
    graph = WorkflowGraph(
        (WorkflowNodeSpec(a), WorkflowNodeSpec(b, (a,)), WorkflowNodeSpec(c, (b,)))
    )
    bindings = [
        WorkflowNodeBinding[int](a, integer),
        WorkflowNodeBinding[int](b, text),
        WorkflowNodeBinding[int](c, none),
    ]
    assert_type(WorkflowNodeBinding[int](a, factory), WorkflowNodeBinding[int])
    assert_type(WorkflowNodeBinding[int](b, CallableHandler()), WorkflowNodeBinding[int])
    executor = SequentialWorkflowExecutor(graph, bindings)
    assert_type(executor, SequentialWorkflowExecutor[int])
    assert_type(bindings[0].node_id, NodeId)
    outcome = await executor.run(3)
    assert_type(outcome, ExecutionResult[Mapping[NodeId, ExecutionResult[object]]])
    assert_type(executor.results[a], ExecutionResult[object])
    assert_type(executor.results[a].value, object)
