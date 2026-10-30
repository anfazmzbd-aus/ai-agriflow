"""Tests for the asynchronous lifecycle contract."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from agentos.base import (
    AgentOSRuntimeError,
    BaseComponent,
    Component,
    LifecycleComponent,
    LifecycleState,
)

Hook = Callable[[], Awaitable[None]]


class ProbeLifecycle(LifecycleComponent):
    """Lifecycle component whose hooks can be observed and controlled by tests."""

    def __init__(self, name: str = "probe") -> None:
        """Create a component with hook call recording and optional actions."""
        super().__init__(name)
        self.calls: list[str] = []
        self.initialize_action: Hook | None = None
        self.start_action: Hook | None = None
        self.stop_action: Hook | None = None

    async def _initialize(self) -> None:
        self.calls.append("initialize")
        if self.initialize_action is not None:
            await self.initialize_action()

    async def _start(self) -> None:
        self.calls.append("start")
        if self.start_action is not None:
            await self.start_action()

    async def _stop(self) -> None:
        self.calls.append("stop")
        if self.stop_action is not None:
            await self.stop_action()


async def wait_for_event(event: asyncio.Event) -> None:
    """Wait for a signal with a bound so a broken hook fails rather than hangs."""
    await asyncio.wait_for(event.wait(), timeout=2)


@pytest.mark.asyncio
async def test_successful_full_lifecycle() -> None:
    """Hooks run in order and each successful public method returns None."""
    component = ProbeLifecycle()

    assert await component.initialize() is None
    assert await component.start() is None
    assert await component.stop() is None
    assert component.lifecycle_state is LifecycleState.STOPPED
    assert component.calls == ["initialize", "start", "stop"]


@pytest.mark.asyncio
async def test_idempotent_calls_do_not_repeat_hooks() -> None:
    """Repeated calls in their idempotent states do not rerun hooks."""
    component = ProbeLifecycle()

    await component.initialize()
    await component.initialize()
    await component.start()
    await component.start()
    await component.stop()
    await component.stop()

    assert component.calls == ["initialize", "start", "stop"]
    assert component.lifecycle_state is LifecycleState.STOPPED


@pytest.mark.asyncio
async def test_invalid_transitions_raise_runtime_error_without_changing_state() -> None:
    """Start-before-initialize and restart-after-stop are rejected."""
    new_component = ProbeLifecycle()
    with pytest.raises(AgentOSRuntimeError, match="cannot start"):
        await new_component.start()
    assert new_component.lifecycle_state is LifecycleState.NEW

    stopped_component = ProbeLifecycle()
    await stopped_component.stop()
    with pytest.raises(AgentOSRuntimeError, match="cannot initialize"):
        await stopped_component.initialize()
    with pytest.raises(AgentOSRuntimeError, match="cannot start"):
        await stopped_component.start()
    assert stopped_component.lifecycle_state is LifecycleState.STOPPED

    started_component = ProbeLifecycle()
    await started_component.initialize()
    await started_component.start()
    with pytest.raises(AgentOSRuntimeError, match="cannot initialize"):
        await started_component.initialize()


@pytest.mark.asyncio
async def test_stop_from_new_does_not_invoke_cleanup() -> None:
    """Stopping a never-initialized component requires no cleanup hook."""
    component = ProbeLifecycle()

    await component.stop()

    assert component.lifecycle_state is LifecycleState.STOPPED
    assert component.calls == []


@pytest.mark.parametrize("hook_name", ["initialize", "start", "stop"])
@pytest.mark.asyncio
async def test_hook_failure_marks_failed_and_propagates_original_exception(
    hook_name: str,
) -> None:
    """Failures from every hook propagate unchanged and mark the lifecycle failed."""
    component = ProbeLifecycle()
    if hook_name != "initialize":
        await component.initialize()
    if hook_name == "stop":
        await component.start()

    expected = RuntimeError(f"{hook_name} failed")

    async def fail() -> None:
        raise expected

    setattr(component, f"{hook_name}_action", fail)
    with pytest.raises(RuntimeError) as captured:
        await getattr(component, hook_name)()

    assert captured.value is expected
    assert component.lifecycle_state is LifecycleState.FAILED
    traceback_names: list[str] = []
    traceback = captured.value.__traceback__
    while traceback is not None:
        traceback_names.append(traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    assert "fail" in traceback_names


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.asyncio
async def test_process_control_exceptions_propagate_without_marking_failed(
    exception_type: type[BaseException],
) -> None:
    """Process-control exceptions escape unchanged and leave state untouched."""
    component = ProbeLifecycle()
    expected = exception_type("stop requested")

    async def interrupt() -> None:
        raise expected

    component.initialize_action = interrupt
    with pytest.raises(exception_type) as captured:
        await component.initialize()

    assert captured.value is expected
    assert component.lifecycle_state is LifecycleState.NEW
    traceback_names: list[str] = []
    traceback = captured.value.__traceback__
    while traceback is not None:
        traceback_names.append(traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    assert "interrupt" in traceback_names


@pytest.mark.asyncio
async def test_failed_component_can_retry_cleanup() -> None:
    """A failed cleanup remains FAILED and a later stop can finish cleanup."""
    component = ProbeLifecycle()
    await component.initialize()
    await component.start()
    fail_cleanup = True

    async def cleanup() -> None:
        nonlocal fail_cleanup
        if fail_cleanup:
            raise RuntimeError("cleanup incomplete")

    component.stop_action = cleanup
    with pytest.raises(RuntimeError, match="cleanup incomplete"):
        await component.stop()
    assert component.lifecycle_state is LifecycleState.FAILED

    fail_cleanup = False
    await component.stop()
    assert component.lifecycle_state is LifecycleState.STOPPED
    assert component.calls.count("stop") == 2


@pytest.mark.asyncio
async def test_failed_initialize_disallows_initialize_and_start_but_allows_cleanup() -> None:
    """A failed initialization cannot resume, but stop can release partial resources."""
    component = ProbeLifecycle()

    async def fail_initialize() -> None:
        raise RuntimeError("initialization incomplete")

    component.initialize_action = fail_initialize
    with pytest.raises(RuntimeError, match="initialization incomplete"):
        await component.initialize()
    with pytest.raises(AgentOSRuntimeError, match="cannot initialize"):
        await component.initialize()
    with pytest.raises(AgentOSRuntimeError, match="cannot start"):
        await component.start()

    await component.stop()
    assert component.lifecycle_state is LifecycleState.STOPPED
    assert component.calls == ["initialize", "stop"]


@pytest.mark.parametrize("hook_name", ["initialize", "start", "stop"])
@pytest.mark.asyncio
async def test_cancellation_during_hook_marks_failed_and_propagates(
    hook_name: str,
) -> None:
    """Cancellation during a running hook is preserved and marks FAILED."""
    component = ProbeLifecycle()
    if hook_name != "initialize":
        await component.initialize()
    if hook_name == "stop":
        await component.start()

    entered = asyncio.Event()
    release = asyncio.Event()

    async def block() -> None:
        entered.set()
        await release.wait()

    setattr(component, f"{hook_name}_action", block)
    task = asyncio.create_task(getattr(component, hook_name)())
    await wait_for_event(entered)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert component.lifecycle_state is LifecycleState.FAILED


class ObservableLock(asyncio.Lock):
    """Lock test double that exposes deterministic evidence of queued waiters."""

    def __init__(self) -> None:
        """Create an asyncio lock with a signal for queued acquisitions."""
        super().__init__()
        self.waiting = asyncio.Event()

    async def acquire(self) -> bool:
        """Acquire the lock, signalling when the caller must wait."""
        if self.locked():
            self.waiting.set()
        return await super().acquire()


@pytest.mark.asyncio
async def test_cancellation_while_waiting_for_lock_does_not_change_state() -> None:
    """A cancelled waiter leaves state transitions to the lock owner."""
    component = ProbeLifecycle()
    lock = ObservableLock()
    component._lifecycle_lock = lock
    entered = asyncio.Event()
    release = asyncio.Event()

    async def block_initialize() -> None:
        entered.set()
        await release.wait()

    component.initialize_action = block_initialize
    initialize_task = asyncio.create_task(component.initialize())
    await wait_for_event(entered)
    stop_task = asyncio.create_task(component.stop())
    await wait_for_event(lock.waiting)
    stop_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await stop_task

    assert component.lifecycle_state is LifecycleState.NEW
    release.set()
    await initialize_task
    assert component.lifecycle_state is LifecycleState.INITIALIZED
    assert component.calls == ["initialize"]


@pytest.mark.asyncio
async def test_concurrent_repeated_lifecycle_calls_are_serialized() -> None:
    """Concurrent repeated calls re-check state after acquiring the lock."""
    component = ProbeLifecycle()
    await asyncio.gather(component.initialize(), component.initialize())
    await asyncio.gather(component.start(), component.start())
    await asyncio.gather(component.stop(), component.stop())

    assert component.calls == ["initialize", "start", "stop"]
    assert component.lifecycle_state is LifecycleState.STOPPED


@pytest.mark.asyncio
async def test_concurrent_start_and_stop_leave_valid_stopped_state() -> None:
    """Contending start/stop calls serialize and reject stale transitions."""
    component = ProbeLifecycle()
    await component.initialize()

    results = await asyncio.gather(component.start(), component.stop(), return_exceptions=True)

    assert component.lifecycle_state is LifecycleState.STOPPED
    assert all(result is None or isinstance(result, AgentOSRuntimeError) for result in results)
    assert component.calls in (["initialize", "start", "stop"], ["initialize", "stop"])


@pytest.mark.asyncio
async def test_recursive_lifecycle_call_fails_instead_of_deadlocking() -> None:
    """A hook that re-enters the public API gets a runtime error, not a hang."""
    component = ProbeLifecycle()

    async def recurse() -> None:
        await component.start()

    component.initialize_action = recurse
    with pytest.raises(AgentOSRuntimeError, match="recursively"):
        await asyncio.wait_for(component.initialize(), timeout=2)

    assert component.lifecycle_state is LifecycleState.FAILED


@pytest.mark.asyncio
async def test_lifecycle_state_is_read_only_and_exports_are_public() -> None:
    """Lifecycle types are available from agentos.base and state has no setter."""
    component = ProbeLifecycle()

    assert isinstance(component, BaseComponent)
    assert isinstance(component, Component)
    assert component.lifecycle_state is LifecycleState.NEW
    with pytest.raises(AttributeError):
        component.lifecycle_state = LifecycleState.STARTED  # type: ignore[misc]


def test_identity_only_components_remain_outside_lifecycle_contract() -> None:
    """Existing Component and BaseComponent users need not implement lifecycle."""
    base_component = BaseComponent("identity-only")

    assert base_component.name == "identity-only"
    assert not hasattr(base_component, "initialize")
    assert not hasattr(base_component, "start")
    assert not hasattr(base_component, "stop")
