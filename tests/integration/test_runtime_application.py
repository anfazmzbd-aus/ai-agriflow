"""Integration tests for application composition and Runtime lifecycle."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from tests.integration.conftest import TestApplication, TraceComponent

from agentos.base import ConfigurationError, LifecycleState
from agentos.container import ServiceContainer
from agentos.core.config import AgentOSSettings
from agentos.events import Event, EventBus
from agentos.manager import ComponentManager
from agentos.registry import Registry
from agentos.runtime import Runtime
from agentos.telemetry import InMemoryTelemetrySink, TelemetryEvent


def test_runtime_core_and_custom_service_identity(application: TestApplication) -> None:
    """Runtime bindings retain identity while an application service is explicit."""
    runtime = application.runtime

    assert runtime.services.resolve(AgentOSSettings) is runtime.settings
    assert runtime.services.resolve(EventBus) is runtime.event_bus
    assert runtime.services.resolve(Registry) is runtime.registry
    assert runtime.services.resolve(InMemoryTelemetrySink) is runtime.telemetry
    assert runtime.services.resolve(ServiceContainer) is runtime.services
    assert runtime.services.resolve(ComponentManager) is runtime.component_manager
    assert runtime.services.resolve(type(application.service)) is application.service
    assert not runtime.services.contains(type(application.agent))
    assert runtime.registry.get("advisor") is application.agent


@pytest.mark.asyncio
async def test_service_container_does_not_manage_registered_service_lifecycle(
    application: TestApplication,
) -> None:
    """Resolving a lifecycle object as a service does not register it with the manager."""
    resource = TraceComponent("container-only", application.trace)
    application.runtime.services.register_instance(TraceComponent, resource)

    await application.runtime.initialize_async()
    await application.runtime.start_async()
    await application.runtime.stop_async()

    assert application.runtime.services.resolve(TraceComponent) is resource
    assert resource.lifecycle_state is LifecycleState.NEW
    assert "initialize:container-only" not in application.trace
    assert "stop:container-only" not in application.trace


@pytest.mark.asyncio
async def test_direct_manager_lifecycle_bypasses_runtime_telemetry(
    application: TestApplication,
) -> None:
    """Calling the manager directly does not run Runtime telemetry policy."""
    await application.runtime.component_manager.initialize()
    await application.runtime.component_manager.start()
    assert application.runtime.state is LifecycleState.STARTED
    assert application.runtime.telemetry.list() == ()

    await application.runtime.component_manager.stop()
    assert application.runtime.state is LifecycleState.STOPPED
    assert application.runtime.telemetry.list() == ()


@pytest.mark.asyncio
async def test_two_runtime_applications_have_independent_state_and_subscriptions(
    app_factory: Callable[[], TestApplication],
) -> None:
    """Separate compositions do not share Runtime-owned mutable collaborators."""
    first, second = app_factory(), app_factory()

    assert first.runtime.component_manager is not second.runtime.component_manager
    assert first.runtime.services is not second.runtime.services
    assert first.runtime.registry is not second.runtime.registry
    assert first.runtime.event_bus is not second.runtime.event_bus
    assert first.runtime.telemetry is not second.runtime.telemetry
    assert first.runtime.services.resolve(type(first.service)) is first.service
    assert second.runtime.services.resolve(type(second.service)) is second.service
    assert first.runtime.registry.get("advisor") is first.agent
    assert second.runtime.registry.get("advisor") is second.agent
    assert first.runtime.state is second.runtime.state is LifecycleState.NEW

    await first.runtime.event_bus.publish(
        Event(type="advice.ready", payload={"goal": "one", "advice": "one"})
    )
    assert len(first.domain_events) == 1
    assert second.domain_events == []


@pytest.mark.asyncio
async def test_lifecycle_order_state_and_post_transition_telemetry(
    application: TestApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The composed graph initializes, starts, and stops in dependency order."""
    telemetry_states: list[tuple[str, LifecycleState]] = []
    original_emit = application.runtime.telemetry.emit

    def record_state_when_emitted(event: TelemetryEvent) -> None:
        telemetry_states.append((event.name, application.runtime.state))
        original_emit(event)

    monkeypatch.setattr(application.runtime.telemetry, "emit", record_state_when_emitted)
    lifecycle_bus_events: list[Event] = []

    async def record_bus_event(event: Event) -> None:
        lifecycle_bus_events.append(event)

    application.runtime.event_bus.subscribe("*", record_bus_event)
    await application.runtime.initialize_async()
    assert application.runtime.state is LifecycleState.INITIALIZED
    assert application.trace == ["initialize:service", "initialize:advisor"]

    await application.runtime.start_async()
    assert application.runtime.state is LifecycleState.STARTED
    assert application.trace == [
        "initialize:service",
        "initialize:advisor",
        "start:service",
        "start:advisor",
    ]

    await application.runtime.stop_async()
    assert application.runtime.state is LifecycleState.STOPPED
    assert application.trace[-2:] == ["stop:advisor", "stop:service"]
    assert [event.name for event in application.runtime.telemetry.list()] == [
        "runtime.initialized",
        "runtime.started",
        "runtime.stopped",
    ]
    assert telemetry_states == [
        ("runtime.initialized", LifecycleState.INITIALIZED),
        ("runtime.started", LifecycleState.STARTED),
        ("runtime.stopped", LifecycleState.STOPPED),
    ]
    assert lifecycle_bus_events == []
    assert application.domain_events == []


@pytest.mark.asyncio
async def test_missing_dependency_preflight_runs_no_hooks_and_keeps_new_state(
    application: TestApplication,
) -> None:
    """A missing dependency fails before hooks and leaves manager state NEW."""
    extra = TraceComponent("extra", application.trace)
    application.runtime.register_component(extra, depends_on=("not-registered",))

    with pytest.raises(ConfigurationError, match="missing dependencies"):
        await application.runtime.initialize_async()

    assert application.runtime.state is LifecycleState.NEW
    assert application.trace == []
    assert application.runtime.telemetry.list() == ()


@pytest.mark.asyncio
async def test_dependency_cycle_preflight_runs_no_hooks_and_keeps_new_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cyclic graph is rejected before component hooks are invoked."""
    import agentos.runtime.runtime as runtime_module

    monkeypatch.setattr(runtime_module, "configure_logging", lambda _: None)
    runtime = Runtime.from_settings(AgentOSSettings(environment="cycle-test"))
    trace: list[str] = []
    first, second = TraceComponent("first", trace), TraceComponent("second", trace)
    runtime.register_component(first, depends_on=("second",))
    runtime.register_component(second, depends_on=("first",))

    with pytest.raises(ConfigurationError, match="dependency cycle"):
        await runtime.initialize_async()

    assert runtime.state is LifecycleState.NEW
    assert trace == []
    assert runtime.telemetry.list() == ()
