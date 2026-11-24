"""Raised errors, cancellation, resource cleanup, and safe diagnostics."""

from __future__ import annotations

import asyncio
from typing import cast

import pytest

from agentos.base import WorkflowError
from agentos.core import ExecutionResult, ExecutionStatus
from agentos.workflows import (
    NodeId,
    SequentialWorkflowExecutor,
    WorkflowGraph,
    WorkflowNodeBinding,
    WorkflowNodeContext,
    WorkflowNodeHandler,
    WorkflowNodeSpec,
)

FIRST = NodeId("first")
FAIL = NodeId("private\n\x1bnode")
LATER = NodeId("later")


def graph() -> WorkflowGraph:
    """Put a failing handler after a completed predecessor."""
    return WorkflowGraph(
        (WorkflowNodeSpec(FIRST), WorkflowNodeSpec(FAIL, (FIRST,)), WorkflowNodeSpec(LATER))
    )


async def successful(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
    """Return a legitimate None."""
    return ExecutionResult[None].success(None)


@pytest.mark.parametrize(
    ("error", "status", "message"),
    [
        (
            ValueError("secret-provider-data"),
            ExecutionStatus.FAILED,
            "workflow node execution failed",
        ),
        (
            WorkflowError("secret-domain-data"),
            ExecutionStatus.FAILED,
            "workflow node execution failed",
        ),
        (
            TimeoutError("secret-timeout"),
            ExecutionStatus.TIMEOUT,
            "workflow node execution timed out",
        ),
        (
            ExceptionGroup("secret-group", [ValueError("secret")]),
            ExecutionStatus.FAILED,
            "workflow node execution failed",
        ),
    ],
)
async def test_exception_chaining_retention_and_cleanup(
    error: Exception, status: ExecutionStatus, message: str
) -> None:
    """Keep exact original causes, completed results, and handler-owned cleanup."""
    cleaned: list[bool] = []

    async def failing(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        try:
            raise error
        finally:
            cleaned.append(True)

    executor = SequentialWorkflowExecutor(
        graph(),
        [
            WorkflowNodeBinding[None](FIRST, successful),
            WorkflowNodeBinding[None](FAIL, failing),
            WorkflowNodeBinding[None](LATER, successful),
        ],
    )
    with pytest.raises(WorkflowError) as captured:
        await executor.run(None)
    assert str(captured.value) == message
    assert captured.value.__cause__ is error
    assert error.__traceback__ is not None
    assert tuple(executor.results) == (FIRST, FAIL)
    assert executor.results[FIRST].status is ExecutionStatus.SUCCESS
    assert executor.results[FAIL].status is status
    assert executor.results[FAIL].error == message
    assert executor.results[FAIL].has_value is False
    assert cleaned == [True]


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(3), BaseException("control")])
async def test_process_control_propagates_without_fabricated_outcome(error: BaseException) -> None:
    """Propagate controls unchanged and retain only completed predecessors."""

    async def fail_once(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        nonlocal error
        current, error = error, None
        if current is not None:
            raise current
        return ExecutionResult[None].success(None)

    executor = SequentialWorkflowExecutor(
        graph(),
        [
            WorkflowNodeBinding[None](FIRST, successful),
            WorkflowNodeBinding[None](FAIL, fail_once),
            WorkflowNodeBinding[None](LATER, successful),
        ],
    )
    original = error
    with pytest.raises(type(original)) as captured:
        await executor.run(None)
    assert captured.value is original
    assert tuple(executor.results) == (FIRST,)
    assert (await executor.run(None)).status is ExecutionStatus.SUCCESS


async def test_actual_cancellation_is_preserved_with_safe_snapshot() -> None:
    """Cancel the actual task, await handler cleanup, retain progress, then reuse."""
    entered, release = asyncio.Event(), asyncio.Event()
    cleaned: list[bool] = []
    cancellation: list[asyncio.CancelledError] = []
    should_block = True

    async def blocking(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        try:
            if should_block:
                entered.set()
                await release.wait()
        except asyncio.CancelledError as exc:
            cancellation.append(exc)
            raise
        finally:
            cleaned.append(True)
        return ExecutionResult[None].success(None)

    executor = SequentialWorkflowExecutor(
        graph(),
        [
            WorkflowNodeBinding[None](FIRST, successful),
            WorkflowNodeBinding[None](FAIL, blocking),
            WorkflowNodeBinding[None](LATER, successful),
        ],
    )
    task = asyncio.create_task(executor.run(None))
    await asyncio.wait_for(entered.wait(), timeout=2)
    during = executor.results
    assert tuple(during) == (FIRST,)
    task.cancel()
    with pytest.raises(asyncio.CancelledError) as captured:
        await task
    assert task.cancelled()
    assert captured.value is cancellation[0]
    assert cleaned == [True]
    retained = executor.results
    assert tuple(retained) == (FIRST, FAIL)
    assert retained[FAIL].status is ExecutionStatus.CANCELLED
    assert retained[FAIL].error == "workflow node execution cancelled"
    assert tuple(during) == (FIRST,)
    should_block = False
    assert (await executor.run(None)).status is ExecutionStatus.SUCCESS
    assert tuple(retained) == (FIRST, FAIL)


async def test_returned_cancelled_is_a_normal_partial_return() -> None:
    """A returned CANCELLED outcome does not cancel the invoking task."""
    outcome = ExecutionResult[None].cancelled()

    async def handler(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        return outcome

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(FIRST),)), [WorkflowNodeBinding[None](FIRST, handler)]
    )
    task = asyncio.create_task(executor.run(None))
    report = await task
    assert not task.cancelled()
    assert report.status is ExecutionStatus.PARTIAL
    assert report.value is not None
    assert report.value[FIRST] is outcome


@pytest.mark.parametrize("invalid", [None, "private-value", object()])
async def test_invalid_returned_result_is_safe(invalid: object) -> None:
    """Runtime checks reject handlers that escape the static contract."""

    async def handler(context: WorkflowNodeContext[None]) -> object:
        return invalid

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(FIRST),)),
        [
            WorkflowNodeBinding[None](FIRST, cast("WorkflowNodeHandler[None, object]", handler)),
        ],
    )
    with pytest.raises(WorkflowError, match=r"^workflow node returned an invalid result$"):
        await executor.run(None)
    assert executor.results[FIRST].status is ExecutionStatus.FAILED


async def test_nonawaitable_return_is_chained_without_preflight_invocation() -> None:
    """Callability is structural; awaitable validation occurs only on invocation."""
    calls: list[bool] = []

    def handler(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        calls.append(True)
        return ExecutionResult[None].success(None)

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(FIRST),)),
        [
            WorkflowNodeBinding[None](FIRST, cast("WorkflowNodeHandler[None, None]", handler)),
        ],
    )
    assert calls == []
    with pytest.raises(WorkflowError) as captured:
        await executor.run(None)
    assert isinstance(captured.value.__cause__, TypeError)
    assert calls == [True]


class Sensitive:
    """Reject diagnostic traversal of payloads and callables."""

    def __repr__(self) -> str:
        """Detect unsafe representation."""
        raise AssertionError("unsafe representation")

    def __str__(self) -> str:
        """Detect unsafe conversion."""
        raise AssertionError("unsafe conversion")

    async def __call__(self, context: WorkflowNodeContext[object]) -> ExecutionResult[object]:
        """Return an opaque object with sensitive metadata."""
        return ExecutionResult[object].success(self, metadata={"private": self})


def test_diagnostics_do_not_inspect_identifiers_or_callables() -> None:
    """Use fixed or positional summaries for all preflight failures."""
    secret = NodeId("private\n\x1bID")
    binding = WorkflowNodeBinding[object](secret, Sensitive())
    executor = SequentialWorkflowExecutor(WorkflowGraph((WorkflowNodeSpec(secret),)), [binding])
    assert repr(binding) == "WorkflowNodeBinding()"
    assert repr(executor) == "SequentialWorkflowExecutor()"
    with pytest.raises(WorkflowError) as duplicate:
        SequentialWorkflowExecutor(WorkflowGraph((WorkflowNodeSpec(secret),)), [binding, binding])
    assert str(duplicate.value) == "duplicate workflow binding at position 2"
    with pytest.raises(WorkflowError) as malformed:
        WorkflowNodeBinding[object](cast("NodeId", Sensitive()), Sensitive())
    assert str(malformed.value) == "workflow binding ID must be a plain nonblank string"


async def test_no_rollback_or_cleanup_hooks_are_invented() -> None:
    """Handler finally blocks own cleanup; completed effects are not undone."""
    effects: list[str] = []

    async def first(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        effects.append("effect")
        return ExecutionResult[None].success(None)

    async def second(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        try:
            return ExecutionResult[None].failure("stop")
        finally:
            effects.append("handler-cleanup")

    executor = SequentialWorkflowExecutor(
        graph(),
        [
            WorkflowNodeBinding[None](FIRST, first),
            WorkflowNodeBinding[None](FAIL, second),
            WorkflowNodeBinding[None](LATER, successful),
        ],
    )
    await executor.run(None)
    assert effects == ["effect", "handler-cleanup"]
