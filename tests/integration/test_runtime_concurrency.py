"""Deterministic integration tests for serialized Runtime lifecycle calls."""

from __future__ import annotations

import asyncio

import pytest
from tests.integration.conftest import TestApplication, TraceComponent, wait_for

from agentos.base import AgentOSRuntimeError, LifecycleState


@pytest.mark.asyncio
async def test_registration_closes_when_runtime_initialization_begins(
    application: TestApplication,
) -> None:
    """Registration from another task is rejected while initialization awaits."""
    entered, release = asyncio.Event(), asyncio.Event()

    async def block_initialize() -> None:
        entered.set()
        await release.wait()

    application.service_component.initialize_hook = block_initialize
    task = asyncio.create_task(application.runtime.initialize_async())
    try:
        await wait_for(entered)
        with pytest.raises(AgentOSRuntimeError, match="cannot register"):
            application.runtime.register_component(TraceComponent("late", application.trace))
    finally:
        release.set()
        await asyncio.wait_for(task, timeout=3)

    assert application.runtime.state is LifecycleState.INITIALIZED


@pytest.mark.asyncio
async def test_concurrent_initialize_requests_run_hooks_once(
    application: TestApplication,
) -> None:
    """A second initialize waits for the active transition and is idempotent."""
    entered, release, second_called = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def block_initialize() -> None:
        entered.set()
        await release.wait()

    application.service_component.initialize_hook = block_initialize
    first = asyncio.create_task(application.runtime.initialize_async())
    second: asyncio.Task[None] | None = None
    try:
        await wait_for(entered)

        async def call_second() -> None:
            second_called.set()
            await application.runtime.initialize_async()

        second = asyncio.create_task(call_second())
        await wait_for(second_called)
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), timeout=3)
    finally:
        release.set()
        if not first.done():
            await first
        if second is not None and not second.done():
            await second

    assert application.runtime.state is LifecycleState.INITIALIZED
    assert application.trace.count("initialize:service") == 1
    assert [event.name for event in application.runtime.telemetry.list()] == ["runtime.initialized"]


@pytest.mark.asyncio
async def test_concurrent_start_requests_emit_one_success_event(
    application: TestApplication,
) -> None:
    """Concurrent starts serialize and call each startup hook once."""
    await application.runtime.initialize_async()
    entered, release, second_called = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def block_start() -> None:
        entered.set()
        await release.wait()

    application.service_component.start_hook = block_start
    first = asyncio.create_task(application.runtime.start_async())
    second: asyncio.Task[None] | None = None
    try:
        await wait_for(entered)

        async def call_second() -> None:
            second_called.set()
            await application.runtime.start_async()

        second = asyncio.create_task(call_second())
        await wait_for(second_called)
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), timeout=3)
    finally:
        release.set()
        if not first.done():
            await first
        if second is not None and not second.done():
            await second

    assert application.runtime.state is LifecycleState.STARTED
    assert application.trace.count("start:service") == 1
    assert [event.name for event in application.runtime.telemetry.list()].count(
        "runtime.started"
    ) == 1
    await application.runtime.stop_async()


@pytest.mark.asyncio
async def test_concurrent_stop_requests_perform_cleanup_once(
    application: TestApplication,
) -> None:
    """Concurrent stops serialize and emit a single stopped event."""
    await application.runtime.initialize_async()
    await application.runtime.start_async()
    entered, release, second_called = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def block_stop() -> None:
        entered.set()
        await release.wait()

    application.agent.stop_hook = block_stop
    first = asyncio.create_task(application.runtime.stop_async())
    second: asyncio.Task[None] | None = None
    try:
        await wait_for(entered)

        async def call_second() -> None:
            second_called.set()
            await application.runtime.stop_async()

        second = asyncio.create_task(call_second())
        await wait_for(second_called)
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), timeout=3)
    finally:
        release.set()
        if not first.done():
            await first
        if second is not None and not second.done():
            await second

    assert application.runtime.state is LifecycleState.STOPPED
    assert application.trace.count("stop:advisor") == 1
    assert [event.name for event in application.runtime.telemetry.list()].count(
        "runtime.stopped"
    ) == 1


@pytest.mark.asyncio
async def test_runtime_lock_waiter_cancellation_does_not_change_manager_state(
    application: TestApplication,
) -> None:
    """Cancellation before acquiring Runtime's lock leaves lifecycle state unchanged."""
    entered, release = asyncio.Event(), asyncio.Event()

    async def block_initialize() -> None:
        entered.set()
        await release.wait()

    application.service_component.initialize_hook = block_initialize
    owner = asyncio.create_task(application.runtime.initialize_async())
    waiter: asyncio.Task[None] | None = None
    try:
        await wait_for(entered)
        waiter_called = asyncio.Event()

        async def wait_to_start() -> None:
            waiter_called.set()
            await application.runtime.start_async()

        waiter = asyncio.create_task(wait_to_start())
        await wait_for(waiter_called)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert application.runtime.state is LifecycleState.NEW
        assert application.runtime.telemetry.list() == ()
    finally:
        release.set()
        await asyncio.wait_for(owner, timeout=3)
        if waiter is not None and not waiter.done():
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter

    assert application.runtime.state is LifecycleState.INITIALIZED


@pytest.mark.asyncio
async def test_same_task_recursive_runtime_lifecycle_fails_without_deadlock(
    application: TestApplication,
) -> None:
    """Recursive lifecycle calls from a managed hook are rejected by Runtime."""

    async def recurse() -> None:
        await application.runtime.stop_async()

    application.agent.initialize_hook = recurse
    with pytest.raises(AgentOSRuntimeError, match="cannot be called recursively"):
        await asyncio.wait_for(application.runtime.initialize_async(), timeout=3)

    assert application.runtime.state is LifecycleState.FAILED
    assert application.runtime.telemetry.list()[-1].name == "runtime.lifecycle_failed"
