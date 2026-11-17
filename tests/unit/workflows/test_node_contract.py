"""Asynchronous callable behavior without an executor or normalization."""

from __future__ import annotations

import asyncio

import pytest

from agentos.base import WorkflowError
from agentos.core import ExecutionResult
from agentos.workflows import NodeId, WorkflowNodeContext, WorkflowNodeHandler


async def test_typed_handler_and_successful_none() -> None:
    """An async function satisfies the callable contract and returns its outcome."""

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[None]:
        assert context.input_data == 3
        return ExecutionResult[None].success(None)

    typed: WorkflowNodeHandler[int, None] = handler
    result = await typed(WorkflowNodeContext(NodeId("root"), 3, {}))
    assert result.has_value
    assert result.value is None


@pytest.mark.parametrize(
    "error",
    [
        ValueError("private provider detail"),
        WorkflowError("domain error"),
        TimeoutError("timeout"),
        asyncio.CancelledError("cancel"),
        KeyboardInterrupt(),
        SystemExit(2),
    ],
)
async def test_raised_exception_identity_is_preserved(error: BaseException) -> None:
    """Manual handler invocation preserves traceback, cause, and control exceptions."""
    cause = RuntimeError("original cause")
    error.__cause__ = cause

    async def handler(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        raise error

    typed: WorkflowNodeHandler[None, None] = handler
    with pytest.raises(type(error)) as captured:
        await typed(WorkflowNodeContext(NodeId("root"), None, {}))
    assert captured.value is error
    assert captured.value.__cause__ is cause
    assert captured.value.__traceback__ is not None


async def test_actual_task_cancellation_propagates() -> None:
    """Cancelling an awaiting handler remains cancellation, not a result."""
    entered = asyncio.Event()
    release = asyncio.Event()

    async def handler(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        entered.set()
        await release.wait()
        return ExecutionResult[None].success(None)

    typed: WorkflowNodeHandler[None, None] = handler

    async def invoke() -> ExecutionResult[None]:
        return await typed(WorkflowNodeContext(NodeId("root"), None, {}))

    task = asyncio.create_task(invoke())
    await asyncio.wait_for(entered.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()
