"""Integration tests for explicitly composed agents and domain events."""

from __future__ import annotations

import asyncio

import pytest
from tests.integration.conftest import TestApplication, wait_for

from agentos.agents import AgentContext
from agentos.base import AgentError, AgentOSRuntimeError, LifecycleState
from agentos.events import Event


@pytest.mark.asyncio
async def test_agent_uses_explicit_service_and_publishes_domain_event(
    application: TestApplication,
) -> None:
    """A Runtime-started agent returns typed output and publishes to its subscriber."""
    await application.runtime.initialize_async()
    await application.runtime.start_async()

    result = await application.agent.run(AgentContext(goal="check soil moisture"))

    assert result.content == "advice:check soil moisture"
    assert result.metadata == {"service": "fake"}
    assert len(application.domain_events) == 1
    assert application.domain_events[0].type == "advice.ready"
    assert application.domain_events[0].payload == {
        "goal": "check soil moisture",
        "advice": "advice:check soil moisture",
    }
    assert application.runtime.state is LifecycleState.STARTED
    await application.runtime.stop_async()


@pytest.mark.asyncio
async def test_agent_admission_is_rejected_before_start_and_after_shutdown(
    application: TestApplication,
) -> None:
    """Agent execution follows Runtime-managed start and stop boundaries."""
    with pytest.raises(AgentOSRuntimeError, match="cannot run agent"):
        await application.agent.run(AgentContext(goal="early"))

    await application.runtime.initialize_async()
    await application.runtime.start_async()
    await application.runtime.stop_async()

    with pytest.raises(AgentOSRuntimeError, match="cannot run agent"):
        await application.agent.run(AgentContext(goal="late"))
    assert application.domain_events == []


@pytest.mark.asyncio
async def test_admitted_agent_run_can_finish_after_runtime_shutdown(
    application: TestApplication,
) -> None:
    """Runtime shutdown does not drain an already-admitted agent execution."""
    entered, release = asyncio.Event(), asyncio.Event()
    application.agent.execution_entered = entered
    application.agent.execution_release = release
    await application.runtime.initialize_async()
    await application.runtime.start_async()
    task = asyncio.create_task(application.agent.run(AgentContext(goal="finish after stop")))

    try:
        await wait_for(entered)
        await application.runtime.stop_async()
        assert application.runtime.state is LifecycleState.STOPPED
    finally:
        release.set()
        if not task.done():
            await asyncio.wait_for(task, timeout=3)

    result = await task
    assert result.content == "advice:finish after stop"
    assert len(application.domain_events) == 1


@pytest.mark.asyncio
async def test_domain_handler_failure_is_fail_fast_and_does_not_fail_runtime(
    application: TestApplication,
) -> None:
    """Agent error wrapping preserves EventBus fail-fast behavior and Runtime state."""
    called: list[str] = []
    handler_error = ValueError("subscriber failed")

    async def fail_handler(_: Event) -> None:
        called.append("first")
        raise handler_error

    async def later_handler(_: Event) -> None:
        called.append("later")

    application.runtime.event_bus.subscribe("advice.ready", fail_handler)
    application.runtime.event_bus.subscribe("advice.ready", later_handler)
    await application.runtime.initialize_async()
    await application.runtime.start_async()

    with pytest.raises(AgentError) as caught:
        await application.agent.run(AgentContext(goal="fail subscriber"))

    assert caught.value.__cause__ is handler_error
    assert called == ["first"]
    assert application.runtime.state is LifecycleState.STARTED
    assert [event.name for event in application.runtime.telemetry.list()] == [
        "runtime.initialized",
        "runtime.started",
    ]
    await application.runtime.stop_async()
