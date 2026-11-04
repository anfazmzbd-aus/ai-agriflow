"""Integration tests for lifecycle failure, rollback, and recovery."""

from __future__ import annotations

import asyncio

import pytest
from tests.integration.conftest import TestApplication, wait_for

from agentos.base import LifecycleState
from agentos.telemetry import TelemetryEvent


@pytest.mark.asyncio
async def test_initialization_failure_rolls_back_then_emits_failure_telemetry(
    application: TestApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime reports failure only after manager rollback has settled."""
    primary = RuntimeError("agent setup failed")

    async def fail_initialize() -> None:
        raise primary

    application.agent.initialize_hook = fail_initialize
    observed_states: list[LifecycleState] = []
    original_emit = application.runtime.telemetry.emit

    def observe_emit(event: TelemetryEvent) -> None:
        if event.name == "runtime.lifecycle_failed":
            observed_states.append(application.runtime.state)
        original_emit(event)

    monkeypatch.setattr(application.runtime.telemetry, "emit", observe_emit)

    with pytest.raises(RuntimeError) as caught:
        await application.runtime.initialize_async()

    assert caught.value is primary
    assert application.runtime.state is LifecycleState.FAILED
    assert application.trace == [
        "initialize:service",
        "initialize:advisor",
        "stop:advisor",
        "stop:service",
    ]
    assert observed_states == [LifecycleState.FAILED]
    assert [event.name for event in application.runtime.telemetry.list()] == [
        "runtime.lifecycle_failed"
    ]


@pytest.mark.asyncio
async def test_startup_failure_aggregates_cleanup_and_runtime_does_not_rollback_twice(
    application: TestApplication,
) -> None:
    """Runtime delegates rollback and preserves both startup and cleanup errors."""
    primary = RuntimeError("agent start failed")
    cleanup = ValueError("service cleanup failed")

    async def fail_start() -> None:
        raise primary

    async def fail_cleanup() -> None:
        raise cleanup

    application.agent.start_hook = fail_start
    application.service_component.stop_hook = fail_cleanup
    await application.runtime.initialize_async()

    with pytest.raises(ExceptionGroup) as caught:
        await application.runtime.start_async()

    assert primary in caught.value.exceptions
    assert cleanup in caught.value.exceptions
    assert application.runtime.state is LifecycleState.FAILED
    assert application.trace == [
        "initialize:service",
        "initialize:advisor",
        "start:service",
        "start:advisor",
        "stop:advisor",
        "stop:service",
    ]
    assert [event.name for event in application.runtime.telemetry.list()] == [
        "runtime.initialized",
        "runtime.lifecycle_failed",
    ]


@pytest.mark.asyncio
async def test_shutdown_attempts_all_cleanup_and_retry_emits_stopped_after_success(
    application: TestApplication,
) -> None:
    """A failed cleanup does not prevent others and can be retried by Runtime."""
    failing = True
    agent_stop_count = 0

    async def fail_once() -> None:
        nonlocal failing, agent_stop_count
        agent_stop_count += 1
        if failing:
            raise RuntimeError("agent cleanup pending")

    application.agent.stop_hook = fail_once
    await application.runtime.initialize_async()
    await application.runtime.start_async()

    with pytest.raises(ExceptionGroup, match="component shutdown failed"):
        await application.runtime.stop_async()

    assert application.runtime.state is LifecycleState.FAILED
    assert application.agent.lifecycle_state is LifecycleState.FAILED
    assert application.service_component.lifecycle_state is LifecycleState.STOPPED
    assert agent_stop_count == 1
    assert "stop:service" in application.trace
    assert "runtime.stopped" not in [event.name for event in application.runtime.telemetry.list()]

    failing = False
    await application.runtime.stop_async()
    assert application.runtime.state is LifecycleState.STOPPED
    assert agent_stop_count == 2
    assert [event.name for event in application.runtime.telemetry.list()] == [
        "runtime.initialized",
        "runtime.started",
        "runtime.lifecycle_failed",
        "runtime.stopped",
    ]


@pytest.mark.asyncio
async def test_cancellation_during_cleanup_propagates_and_runtime_can_retry(
    application: TestApplication,
) -> None:
    """Hook cancellation propagates, remaining cleanup runs, and retry can finish."""
    entered, release = asyncio.Event(), asyncio.Event()
    cleanup_calls = 0

    async def block_cleanup() -> None:
        nonlocal cleanup_calls
        cleanup_calls += 1
        entered.set()
        await release.wait()

    application.agent.stop_hook = block_cleanup
    await application.runtime.initialize_async()
    await application.runtime.start_async()
    task = asyncio.create_task(application.runtime.stop_async())

    try:
        await wait_for(entered)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        release.set()
        if not task.done():
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    assert application.runtime.state is LifecycleState.FAILED
    assert application.service_component.lifecycle_state is LifecycleState.STOPPED
    assert cleanup_calls == 1
    assert [event.name for event in application.runtime.telemetry.list()][-1] == (
        "runtime.lifecycle_failed"
    )

    application.agent.stop_hook = None
    await application.runtime.stop_async()
    assert application.runtime.state is LifecycleState.STOPPED
    assert cleanup_calls == 1
    assert application.trace.count("stop:advisor") == 2
    assert application.trace.count("stop:service") == 1
    assert [event.name for event in application.runtime.telemetry.list()][-1] == ("runtime.stopped")


@pytest.mark.parametrize("control_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.asyncio
async def test_cleanup_control_exception_keeps_startup_failure_as_cause(
    application: TestApplication,
    control_type: type[BaseException],
) -> None:
    """Inline process-control cleanup propagation preserves identity and cause."""
    primary = RuntimeError("startup failed")
    control = control_type("cleanup interrupted")

    async def fail_start() -> None:
        raise primary

    async def interrupt_cleanup() -> None:
        raise control

    application.agent.start_hook = fail_start
    application.agent.stop_hook = interrupt_cleanup
    await application.runtime.initialize_async()

    with pytest.raises(control_type) as caught:
        await application.runtime.start_async()

    assert caught.value is control
    assert control.__cause__ is primary
    assert not isinstance(control, ExceptionGroup)
    assert any("startup rollback" in note for note in control.__notes__)
    assert application.runtime.state is LifecycleState.FAILED


@pytest.mark.asyncio
async def test_ordinary_telemetry_failure_does_not_change_managed_lifecycle(
    application: TestApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ordinary telemetry failure is suppressed after a successful transition."""
    original_emit = application.runtime.telemetry.emit

    def fail_start_event(event: TelemetryEvent) -> None:
        if event.name == "runtime.started":
            raise RuntimeError("telemetry unavailable")
        original_emit(event)

    monkeypatch.setattr(application.runtime.telemetry, "emit", fail_start_event)
    await application.runtime.initialize_async()
    await application.runtime.start_async()

    assert application.runtime.state is LifecycleState.STARTED
    assert [event.name for event in application.runtime.telemetry.list()] == ["runtime.initialized"]
    await application.runtime.stop_async()


@pytest.mark.asyncio
async def test_control_flow_telemetry_failure_propagates_after_started_transition(
    application: TestApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Telemetry process control propagates only after Runtime reaches STARTED."""
    control = KeyboardInterrupt("telemetry interrupted")
    original_emit = application.runtime.telemetry.emit

    def interrupt_started_event(event: TelemetryEvent) -> None:
        if event.name == "runtime.started":
            raise control
        original_emit(event)

    monkeypatch.setattr(application.runtime.telemetry, "emit", interrupt_started_event)
    await application.runtime.initialize_async()

    with pytest.raises(KeyboardInterrupt) as caught:
        await application.runtime.start_async()

    assert caught.value is control
    assert application.runtime.state is LifecycleState.STARTED
    await application.runtime.stop_async()
