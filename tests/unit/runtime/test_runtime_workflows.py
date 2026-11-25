"""Runtime workflow admission, shutdown races, delegation, and recovery contracts."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import fields
from inspect import signature

import pytest

from agentos.base import AgentOSRuntimeError, LifecycleComponent, LifecycleState, WorkflowError
from agentos.core import ExecutionResult, ExecutionStatus
from agentos.core.config import AgentOSSettings
from agentos.runtime import Runtime
from agentos.workflows import (
    NodeId,
    SequentialWorkflowExecutor,
    WorkflowGraph,
    WorkflowNodeBinding,
    WorkflowNodeContext,
    WorkflowNodeHandler,
    WorkflowNodeSpec,
)

NODE = NodeId("private\n\x1bnode")
Hook = Callable[[], Awaitable[None]]


class Probe(LifecycleComponent):
    """Observe real managed component hooks without modifying manager internals."""

    def __init__(self) -> None:
        """Create a probe with optional suspended or failing hooks."""
        super().__init__("resource")
        self.calls: list[str] = []
        self.start_hook: Hook | None = None
        self.stop_hook: Hook | None = None

    async def _initialize(self) -> None:
        self.calls.append("initialize")

    async def _start(self) -> None:
        self.calls.append("start")
        if self.start_hook is not None:
            await self.start_hook()

    async def _stop(self) -> None:
        self.calls.append("stop")
        if self.stop_hook is not None:
            await self.stop_hook()


def make_runtime() -> Runtime:
    """Use explicit settings and independent default manager/service ownership."""
    return Runtime.from_settings(AgentOSSettings(environment="test", log_level="WARNING"))


async def ready(runtime: Runtime) -> None:
    """Perform actual managed startup."""
    await runtime.initialize_async()
    await runtime.start_async()


async def wait(event: asyncio.Event) -> None:
    """Bound barrier waits only in the test harness."""
    await asyncio.wait_for(event.wait(), timeout=2)


async def integer(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
    """Return typed input without external effects."""
    return ExecutionResult[int].success(context.input_data)


def executor_for[InputT, OutputT](
    handler: WorkflowNodeHandler[InputT, OutputT],
) -> SequentialWorkflowExecutor[InputT]:
    """Construct a real executor with one graph-local handler."""
    return SequentialWorkflowExecutor(
        WorkflowGraph((WorkflowNodeSpec(NODE),)), [WorkflowNodeBinding[InputT](NODE, handler)]
    )


class ObservedExecutor(SequentialWorkflowExecutor[int]):
    """Observe delegation identity while retaining the real executor implementation."""

    def __init__(self, runtime: Runtime, handler: WorkflowNodeHandler[int, None]) -> None:
        """Bind a handler and capture report/error identity at the delegation boundary."""
        super().__init__(
            WorkflowGraph((WorkflowNodeSpec(NODE),)), [WorkflowNodeBinding[int](NODE, handler)]
        )
        self.runtime = runtime
        self.report: ExecutionResult[Mapping[NodeId, ExecutionResult[object]]] | None = None
        self.raised: BaseException | None = None
        self.task: asyncio.Task[object] | None = None
        self.lifecycle_lock_held = False

    async def run(
        self, input_data: int
    ) -> ExecutionResult[Mapping[NodeId, ExecutionResult[object]]]:
        """Delegate in the same task, recording only observable boundary values."""
        self.task = asyncio.current_task()
        self.lifecycle_lock_held = self.runtime._lifecycle_lock.locked()
        try:
            self.report = await super().run(input_data)
        except BaseException as exc:
            self.raised = exc
            raise
        return self.report


@pytest.mark.parametrize(
    "node_result",
    [
        ExecutionResult[None].success(None),
        ExecutionResult[None].failure("private failure"),
        ExecutionResult[None].partial(None),
        ExecutionResult[None].retry(),
        ExecutionResult[None].timeout("private timeout"),
        ExecutionResult[None].cancelled(),
    ],
)
async def test_reports_statuses_identity_and_no_workflow_telemetry(
    node_result: ExecutionResult[None],
) -> None:
    """Return the exact executor report and node outcome without lifecycle changes."""
    runtime = make_runtime()
    await ready(runtime)
    telemetry = runtime.telemetry.list()

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[None]:
        return node_result

    executor = ObservedExecutor(runtime, handler)
    report = await runtime.run_workflow(executor, 7)
    assert report is executor.report
    assert report.value is not None
    assert report.value[NODE] is node_result
    assert report.value[NODE].has_value is node_result.has_value
    expected = (
        ExecutionStatus.SUCCESS
        if node_result.status is ExecutionStatus.SUCCESS
        else ExecutionStatus.PARTIAL
    )
    assert report.status is expected
    assert executor.task is asyncio.current_task()
    assert not executor.lifecycle_lock_held
    assert runtime.state is LifecycleState.STARTED
    assert runtime.telemetry.list() == telemetry
    await runtime.stop_async()


@pytest.mark.parametrize("checkpoint", ["new", "legacy", "initialized", "stopped", "failed"])
async def test_invalid_lifecycle_admission_preserves_executor(checkpoint: str) -> None:
    """Reject every non-STARTED state, including legacy start, before delegation."""
    runtime = make_runtime()
    if checkpoint == "legacy":
        runtime.start()
    elif checkpoint == "initialized":
        await runtime.initialize_async()
    elif checkpoint == "stopped":
        await ready(runtime)
        await runtime.stop_async()
    elif checkpoint == "failed":
        component = Probe()

        async def fail() -> None:
            raise ValueError("startup")

        component.start_hook = fail
        runtime.register_component(component)
        await runtime.initialize_async()
        with pytest.raises(ValueError, match="startup"):
            await runtime.start_async()
    assert (
        runtime.state
        is {
            "new": LifecycleState.NEW,
            "legacy": LifecycleState.NEW,
            "initialized": LifecycleState.INITIALIZED,
            "stopped": LifecycleState.STOPPED,
            "failed": LifecycleState.FAILED,
        }[checkpoint]
    )
    executor = executor_for(integer)
    await executor.run(1)
    prior, state, telemetry = executor.results, runtime.state, runtime.telemetry.list()
    with pytest.raises(AgentOSRuntimeError) as caught:
        await runtime.run_workflow(executor, 2)
    assert str(caught.value) == "Runtime workflow execution requires STARTED state"
    assert executor.results is prior
    assert prior[NODE].value == 1
    assert runtime.state is state
    assert runtime.telemetry.list() == telemetry


async def test_workflow_first_rejects_shutdown_before_teardown_and_telemetry() -> None:
    """An admitted suspended workflow prevents managed stop, which can be retried."""
    runtime, component = make_runtime(), Probe()
    runtime.register_component(component)
    await ready(runtime)
    entered, release = asyncio.Event(), asyncio.Event()

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        entered.set()
        await release.wait()
        return ExecutionResult[int].success(context.input_data)

    executor = executor_for(handler)
    task = asyncio.create_task(runtime.run_workflow(executor, 1))
    await wait(entered)
    calls, telemetry = component.calls.copy(), runtime.telemetry.list()
    try:
        with pytest.raises(AgentOSRuntimeError) as caught:
            await runtime.stop_async()
        assert str(caught.value) == "Runtime cannot stop while a managed workflow is active"
        assert component.calls == calls
        assert component.lifecycle_state is LifecycleState.STARTED
        assert runtime.state is LifecycleState.STARTED
        assert runtime.telemetry.list() == telemetry
        assert not task.done()
    finally:
        release.set()
        await task
    await runtime.stop_async()
    assert component.calls == ["initialize", "start", "stop"]
    assert runtime.state is LifecycleState.STOPPED
    assert [e.name for e in runtime.telemetry.list()] == [
        "runtime.initialized",
        "runtime.started",
        "runtime.stopped",
    ]


async def test_shutdown_first_rejects_workflow_even_while_state_is_started() -> None:
    """A suspended teardown hook holds lifecycle admission before aggregate state changes."""
    runtime, component = make_runtime(), Probe()
    entered, release = asyncio.Event(), asyncio.Event()

    async def stopping() -> None:
        entered.set()
        await release.wait()

    component.stop_hook = stopping
    runtime.register_component(component)
    await ready(runtime)
    executor = executor_for(integer)
    await executor.run(1)
    prior, telemetry = executor.results, runtime.telemetry.list()
    shutdown = asyncio.create_task(runtime.stop_async())
    await wait(entered)
    try:
        assert runtime.state is LifecycleState.STARTED
        with pytest.raises(AgentOSRuntimeError) as caught:
            await runtime.run_workflow(executor, 2)
        assert str(caught.value) == (
            "Runtime workflow execution is unavailable during lifecycle operations"
        )
        assert executor.results is prior
        assert runtime.telemetry.list() == telemetry
        assert component.calls == ["initialize", "start", "stop"]
    finally:
        release.set()
        await shutdown
    assert runtime.state is LifecycleState.STOPPED


@pytest.mark.parametrize("same_executor", [True, False])
async def test_overlapping_calls_do_not_disturb_active_or_rejected_executor(
    same_executor: bool,
) -> None:
    """Runtime rejects overlap across both the same and different executor instances."""
    runtime = make_runtime()
    await ready(runtime)
    entered, release = asyncio.Event(), asyncio.Event()

    async def blocking(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        entered.set()
        await release.wait()
        return ExecutionResult[int].success(context.input_data)

    active = executor_for(blocking)
    other = executor_for(integer)
    await other.run(9)
    previous = other.results
    task = asyncio.create_task(runtime.run_workflow(active, 1))
    await wait(entered)
    try:
        with pytest.raises(AgentOSRuntimeError, match=r"^Runtime already has an active workflow$"):
            await runtime.run_workflow(active if same_executor else other, 2)
        assert active.results == {}
        assert other.results is previous
        assert not task.done()
    finally:
        release.set()
        await task
    assert (await runtime.run_workflow(other, 3)).status is ExecutionStatus.SUCCESS
    await runtime.stop_async()


@pytest.mark.parametrize("same_executor", [True, False])
async def test_nested_calls_are_rejected_without_deadlock(same_executor: bool) -> None:
    """Same-task nesting is rejected before executor admission and does not clear the owner."""
    runtime = make_runtime()
    await ready(runtime)
    other = executor_for(integer)

    async def nested(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        with pytest.raises(AgentOSRuntimeError, match=r"^Runtime already has an active workflow$"):
            await runtime.run_workflow(active if same_executor else other, 2)
        with pytest.raises(AgentOSRuntimeError, match="cannot stop while a managed workflow"):
            await runtime.stop_async()
        return ExecutionResult[int].success(context.input_data)

    active = executor_for(nested)
    result = await asyncio.wait_for(runtime.run_workflow(active, 1), timeout=2)
    assert result.value is not None
    assert result.value[NODE].value == 1
    await runtime.stop_async()


async def test_independent_runtimes_and_executors_can_run_concurrently() -> None:
    """Separate Runtime managers and executor stores have independent admission."""
    left, right = make_runtime(), make_runtime()
    assert left.component_manager is not right.component_manager
    await ready(left)
    await ready(right)
    both, release = asyncio.Event(), asyncio.Event()
    count = 0

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        nonlocal count
        count += 1
        if count == 2:
            both.set()
        await release.wait()
        return ExecutionResult[int].success(context.input_data)

    a, b = executor_for(handler), executor_for(handler)
    tasks = [
        asyncio.create_task(left.run_workflow(a, 1)),
        asyncio.create_task(right.run_workflow(b, 2)),
    ]
    try:
        await wait(both)
        assert count == 2
    finally:
        release.set()
        await asyncio.gather(*tasks)
    assert a.results[NODE].value == 1
    assert b.results[NODE].value == 2
    await left.stop_async()
    await right.stop_async()


async def test_standalone_executor_admission_error_releases_runtime_admission() -> None:
    """A busy executor keeps its WorkflowError; Runtime can immediately admit another."""
    runtime = make_runtime()
    await ready(runtime)
    entered, release = asyncio.Event(), asyncio.Event()

    async def blocking(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        entered.set()
        await release.wait()
        return ExecutionResult[int].success(context.input_data)

    busy = executor_for(blocking)
    standalone = asyncio.create_task(busy.run(1))
    await wait(entered)
    prior = busy.results
    try:
        with pytest.raises(WorkflowError) as caught:
            await runtime.run_workflow(busy, 2)
        assert str(caught.value) == "workflow executor already has an active run"
        assert busy.results == prior
        assert not standalone.done()
        assert (
            await runtime.run_workflow(executor_for(integer), 3)
        ).status is ExecutionStatus.SUCCESS
    finally:
        release.set()
        await standalone
    assert (await runtime.run_workflow(busy, 4)).status is ExecutionStatus.SUCCESS
    await runtime.stop_async()


async def test_repeated_runs_retain_independent_snapshots_and_core_bindings() -> None:
    """Runtime neither owns nor resets executor retention and preserves service identities."""
    runtime = make_runtime()
    await ready(runtime)
    manager, services = runtime.component_manager, runtime.services
    executor = executor_for(integer)
    first = await runtime.run_workflow(executor, 1)
    prior = executor.results
    second = await runtime.run_workflow(executor, 2)
    assert first.value is not None
    assert second.value is not None
    assert first.value[NODE] is prior[NODE]
    assert first.value[NODE] is not second.value[NODE]
    assert prior[NODE].value == 1
    assert second.value[NODE].value == 2
    assert runtime.component_manager is manager
    assert runtime.services is services
    assert services.resolve(type(manager)) is manager
    await runtime.stop_async()


@pytest.mark.parametrize(
    "error",
    [
        ValueError("private failure"),
        WorkflowError("private workflow failure"),
        TimeoutError("private timeout"),
        asyncio.CancelledError("private cancellation"),
        KeyboardInterrupt("private control"),
        SystemExit(4),
        BaseException("private base"),
    ],
)
async def test_exception_identity_causes_and_recovery(error: BaseException) -> None:
    """Preserve executor errors/controls and settle admission before subsequent runs."""
    runtime = make_runtime()
    await ready(runtime)
    calls = 0

    async def fail_once(context: WorkflowNodeContext[int]) -> ExecutionResult[None]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise error
        return ExecutionResult[None].success(None)

    executor = ObservedExecutor(runtime, fail_once)
    telemetry = runtime.telemetry.list()
    expected_type = WorkflowError if isinstance(error, Exception) else type(error)
    with pytest.raises(expected_type) as caught:
        await runtime.run_workflow(executor, 1)
    assert caught.value is executor.raised
    if isinstance(error, Exception):
        assert caught.value.__cause__ is error
        assert "private" not in str(caught.value)
        expected_status = (
            ExecutionStatus.TIMEOUT if isinstance(error, TimeoutError) else ExecutionStatus.FAILED
        )
        assert executor.results[NODE].status is expected_status
    else:
        assert caught.value is error
        if isinstance(error, asyncio.CancelledError):
            assert executor.results[NODE].status is ExecutionStatus.CANCELLED
        else:
            assert executor.results == {}
    prior = executor.results
    assert runtime.state is LifecycleState.STARTED
    assert runtime.telemetry.list() == telemetry
    assert (await runtime.run_workflow(executor, 2)).status is ExecutionStatus.SUCCESS
    assert executor.results[NODE].has_value
    assert prior is not executor.results
    await runtime.stop_async()


async def test_actual_caller_cancellation_cleanup_reuse_and_shutdown() -> None:
    """Cancellation reaches the handler in the caller task and releases both owners."""
    runtime, component = make_runtime(), Probe()
    runtime.register_component(component)
    await ready(runtime)
    entered, release = asyncio.Event(), asyncio.Event()
    cleaned: list[bool] = []
    cancellations: list[asyncio.CancelledError] = []
    block = True

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[None]:
        try:
            if block:
                entered.set()
                await release.wait()
        except asyncio.CancelledError as exc:
            cancellations.append(exc)
            raise
        finally:
            cleaned.append(True)
        return ExecutionResult[None].success(None)

    executor = ObservedExecutor(runtime, handler)
    telemetry = runtime.telemetry.list()
    caller = asyncio.create_task(runtime.run_workflow(executor, 1))
    await wait(entered)
    caller.cancel()
    with pytest.raises(asyncio.CancelledError) as caught:
        await caller
    assert caught.value is cancellations[0] is executor.raised
    assert caller.cancelled()
    assert executor.task is caller
    assert cleaned == [True]
    prior = executor.results
    assert prior[NODE].status is ExecutionStatus.CANCELLED
    assert runtime.state is LifecycleState.STARTED
    assert component.calls == ["initialize", "start"]
    assert runtime.telemetry.list() == telemetry
    block = False
    assert (await runtime.run_workflow(executor, 2)).status is ExecutionStatus.SUCCESS
    assert prior[NODE].status is ExecutionStatus.CANCELLED
    await runtime.stop_async()
    assert component.calls == ["initialize", "start", "stop"]


def test_private_flag_preserves_constructor_representation_and_comparison_contract() -> None:
    """The one new flag is private to execution, not constructor/repr/equality."""
    flag = next(f for f in fields(Runtime) if f.name == "_workflow_active")
    assert (flag.init, flag.repr, flag.compare, flag.default) == (False, False, False, False)
    assert list(signature(Runtime).parameters) == [
        "settings",
        "event_bus",
        "registry",
        "telemetry",
        "services",
        "component_manager",
    ]
    assert "_workflow_active" not in repr(make_runtime())


@pytest.mark.parametrize("shared_runtime", [False, True])
async def test_direct_or_shared_manager_lifecycle_calls_bypass_guard(shared_runtime: bool) -> None:
    """Document the narrow guarantee through observable existing manager behavior."""
    runtime, component = make_runtime(), Probe()
    runtime.register_component(component)
    await ready(runtime)
    entered, release = asyncio.Event(), asyncio.Event()

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        entered.set()
        await release.wait()
        return ExecutionResult[int].success(context.input_data)

    task = asyncio.create_task(runtime.run_workflow(executor_for(handler), 1))
    await wait(entered)
    try:
        if shared_runtime:
            other = Runtime(
                runtime.settings,
                runtime.event_bus,
                runtime.registry,
                runtime.telemetry,
                component_manager=runtime.component_manager,
            )
            await other.stop_async()
        else:
            await runtime.component_manager.stop()
        assert runtime.state is LifecycleState.STOPPED
        assert component.calls == ["initialize", "start", "stop"]
        assert not task.done()
    finally:
        release.set()
        await task
