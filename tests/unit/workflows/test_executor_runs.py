"""Run isolation, snapshot lifetime, admission, and absence of hidden policy."""

from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
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
    WorkflowNodeSpec,
)

ROOT = NodeId("root")


async def test_repeated_runs_and_snapshots_are_independent() -> None:
    """Create a fresh store and preserve old mapping and outcome identities."""
    observed: list[object] = []

    async def handler(context: WorkflowNodeContext[list[int]]) -> ExecutionResult[list[int]]:
        observed.append(context.input_data)
        assert executor.results == {}
        return ExecutionResult[list[int]].success(context.input_data)

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(ROOT),)), [WorkflowNodeBinding[list[int]](ROOT, handler)]
    )
    initial = executor.results
    first_input, second_input = [1], [2]
    first = await executor.run(first_input)
    prior = executor.results
    second = await executor.run(second_input)
    assert initial == {}
    assert first.value is not None
    assert second.value is not None
    assert first.value[ROOT] is prior[ROOT]
    assert first.value[ROOT] is not second.value[ROOT]
    assert observed[0] is first_input
    assert observed[1] is second_input
    first_input.append(3)
    assert prior[ROOT].value == [1, 3]
    with pytest.raises(TypeError):
        cast("MutableMapping[NodeId, ExecutionResult[object]]", prior)[ROOT] = prior[ROOT]
    assert not hasattr(executor, "__dict__")


async def test_overlapping_calls_are_rejected_without_disturbing_active_run() -> None:
    """Reject rather than queue a second call, preserving the first run."""
    entered, release = asyncio.Event(), asyncio.Event()
    calls: list[int] = []

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        calls.append(context.input_data)
        entered.set()
        await release.wait()
        return ExecutionResult[int].success(context.input_data)

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(ROOT),)), [WorkflowNodeBinding[int](ROOT, handler)]
    )
    first = asyncio.create_task(executor.run(1))
    await asyncio.wait_for(entered.wait(), timeout=2)
    snapshot = executor.results
    with pytest.raises(WorkflowError, match="already has an active run"):
        await executor.run(2)
    assert executor.results == snapshot == {}
    assert not first.done()
    release.set()
    report = await first
    assert report.value is not None
    assert report.value[ROOT].value == 1
    assert calls == [1]
    assert (await executor.run(3)).status is ExecutionStatus.SUCCESS


async def test_same_task_reentrancy_is_rejected_without_deadlock() -> None:
    """A handler may catch admission rejection and finish its original invocation."""

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        with pytest.raises(WorkflowError, match="already has an active run"):
            await executor.run(9)
        return ExecutionResult[int].success(context.input_data)

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(ROOT),)), [WorkflowNodeBinding[int](ROOT, handler)]
    )
    report = await executor.run(4)
    assert report.value is not None
    assert report.value[ROOT].value == 4


async def test_different_instances_can_run_concurrently() -> None:
    """Separate owners may share topology and handlers without shared result stores."""
    both_entered, release = asyncio.Event(), asyncio.Event()
    count = 0

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        nonlocal count
        count += 1
        if count == 2:
            both_entered.set()
        await release.wait()
        return ExecutionResult[int].success(context.input_data)

    graph = WorkflowGraph((WorkflowNodeSpec(ROOT),))
    binding = WorkflowNodeBinding[int](ROOT, handler)
    left, right = (
        SequentialWorkflowExecutor(graph, [binding]),
        SequentialWorkflowExecutor(graph, [binding]),
    )
    tasks = [asyncio.create_task(left.run(1)), asyncio.create_task(right.run(2))]
    await asyncio.wait_for(both_entered.wait(), timeout=2)
    release.set()
    outcomes = await asyncio.gather(*tasks)
    assert outcomes[0].value is not None
    assert outcomes[1].value is not None
    assert outcomes[0].value[ROOT].value == 1
    assert outcomes[1].value[ROOT].value == 2
    assert left.results[ROOT] is not right.results[ROOT]


@pytest.mark.parametrize(
    "result",
    [
        ExecutionResult[None].retry(),
        ExecutionResult[None].timeout("safe timeout"),
        ExecutionResult[None].partial(None),
        ExecutionResult[None].cancelled(),
    ],
)
async def test_no_implicit_retry_or_status_terminal_loop(result: ExecutionResult[None]) -> None:
    """Invoke once even for statuses whose helper says nonterminal."""
    calls: list[int] = []

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[None]:
        calls.append(context.input_data)
        return result

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(ROOT),)), [WorkflowNodeBinding[int](ROOT, handler)]
    )
    for value in (1, 2):
        report = await executor.run(value)
        assert report.status is ExecutionStatus.PARTIAL
    assert calls == [1, 2]


async def test_waiting_handler_is_not_given_a_hidden_timeout() -> None:
    """Remain pending until the caller releases the handler."""
    entered, release = asyncio.Event(), asyncio.Event()

    async def handler(context: WorkflowNodeContext[None]) -> ExecutionResult[None]:
        entered.set()
        await release.wait()
        return ExecutionResult[None].success(None)

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(ROOT),)), [WorkflowNodeBinding[None](ROOT, handler)]
    )
    task = asyncio.create_task(executor.run(None))
    await asyncio.wait_for(entered.wait(), timeout=2)
    assert not task.done()
    release.set()
    assert (await task).status is ExecutionStatus.SUCCESS


async def test_cancellation_before_admission_preserves_previous_snapshot() -> None:
    """Cancelling a task before its coroutine starts does not reset retained results."""

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        return ExecutionResult[int].success(context.input_data)

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(ROOT),)), [WorkflowNodeBinding[int](ROOT, handler)]
    )
    await executor.run(1)
    previous = executor.results
    task = asyncio.create_task(executor.run(2))
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert executor.results is previous


async def test_executor_can_be_reused_after_an_ordinary_exception() -> None:
    """Release admission on errors and preserve the previous failed snapshot."""
    calls = 0
    original = ValueError("private cause")

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        nonlocal calls
        calls += 1
        assert executor.results == {}
        if calls == 1:
            raise original
        return ExecutionResult[int].success(context.input_data)

    executor = SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(ROOT),)),
        [WorkflowNodeBinding[int](ROOT, handler)],
    )
    with pytest.raises(WorkflowError) as captured:
        await executor.run(1)
    assert captured.value.__cause__ is original
    failed = executor.results
    assert failed[ROOT].status is ExecutionStatus.FAILED
    report = await executor.run(2)
    assert report.value is not None
    assert report.value[ROOT].value == 2
    assert failed[ROOT].status is ExecutionStatus.FAILED
    assert report.value[ROOT] is not failed[ROOT]
