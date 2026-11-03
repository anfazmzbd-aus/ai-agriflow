from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from agentos.agents import AgentContext, AgentResult, BaseAgent
from agentos.base import AgentOSRuntimeError, LifecycleComponent, LifecycleState, ServiceError
from agentos.container import ServiceContainer
from agentos.core.config import AgentOSSettings
from agentos.events import Event, EventBus
from agentos.manager import ComponentManager
from agentos.registry import Registry
from agentos.runtime import Runtime
from agentos.telemetry import InMemoryTelemetrySink, TelemetryEvent

Hook = Callable[[], Awaitable[None]]


def test_runtime_can_be_created_from_settings() -> None:
    """Runtime should preserve explicit settings."""
    settings = AgentOSSettings(environment="test", log_level="WARNING")

    runtime = Runtime.from_settings(settings)

    assert runtime.settings == settings


class RuntimeProbe(LifecycleComponent):
    """Lifecycle probe for Runtime integration tests."""

    def __init__(self, name: str, calls: list[str] | None = None) -> None:
        """Create an observable component."""
        super().__init__(name)
        self.calls = calls if calls is not None else []
        self.initialize_hook: Hook | None = None
        self.start_hook: Hook | None = None
        self.stop_hook: Hook | None = None

    async def _initialize(self) -> None:
        self.calls.append(f"initialize:{self.name}")
        if self.initialize_hook is not None:
            await self.initialize_hook()

    async def _start(self) -> None:
        self.calls.append(f"start:{self.name}")
        if self.start_hook is not None:
            await self.start_hook()

    async def _stop(self) -> None:
        self.calls.append(f"stop:{self.name}")
        if self.stop_hook is not None:
            await self.stop_hook()


class FaultyTelemetry(InMemoryTelemetrySink):
    """Sink that can fail selected lifecycle telemetry emissions."""

    def __init__(self, failure: BaseException, event_name: str) -> None:
        """Create a sink configured with one failure."""
        super().__init__()
        self.failure = failure
        self.event_name = event_name

    def emit(self, event: TelemetryEvent) -> None:
        """Raise the configured exception for the selected event name."""
        if event.name == self.event_name:
            raise self.failure
        super().emit(event)


def make_runtime(
    *, telemetry: InMemoryTelemetrySink | None = None, services: ServiceContainer | None = None
) -> Runtime:
    """Build a Runtime with explicit components for lifecycle tests."""
    return Runtime(
        AgentOSSettings(environment="test", log_level="WARNING"),
        EventBus(),
        Registry(),
        telemetry or InMemoryTelemetrySink(),
        services=services or ServiceContainer(),
    )


async def wait_for(event: asyncio.Event) -> None:
    """Wait deterministically with a finite test bound."""
    await asyncio.wait_for(event.wait(), timeout=2)


def test_four_argument_runtime_construction_and_core_service_identity() -> None:
    """Four positional fields remain compatible and core keys preserve identity."""
    settings = AgentOSSettings(environment="manual")
    bus, registry, telemetry = EventBus(), Registry(), InMemoryTelemetrySink()
    runtime = Runtime(settings, bus, registry, telemetry)

    assert runtime.settings is settings
    assert runtime.event_bus is bus
    assert runtime.registry is registry
    assert runtime.telemetry is telemetry
    assert runtime.services.resolve(AgentOSSettings) is settings
    assert runtime.services.resolve(EventBus) is bus
    # Generic Registry aliases are not distinct runtime class keys.
    assert runtime.services.resolve(Registry) is registry
    assert runtime.services.resolve(InMemoryTelemetrySink) is telemetry
    assert runtime.services.resolve(ServiceContainer) is runtime.services
    assert runtime.services.resolve(ComponentManager) is runtime.component_manager
    assert runtime.state is LifecycleState.NEW


def test_from_settings_constructs_managed_dependencies() -> None:
    """Factory construction supplies the manager and service container."""
    settings = AgentOSSettings(environment="factory")
    runtime = Runtime.from_settings(settings)
    assert runtime.settings is settings
    assert isinstance(runtime.services, ServiceContainer)
    assert isinstance(runtime.component_manager, ComponentManager)
    assert runtime.services.resolve(Registry) is runtime.registry


def test_unrelated_user_services_are_preserved() -> None:
    """Core binding setup preserves registrations under unrelated keys."""

    class UserService:
        pass

    custom = UserService()
    services = ServiceContainer()
    services.register_instance(UserService, custom)
    runtime = make_runtime(services=services)
    assert runtime.services.resolve(UserService) is custom


def test_core_key_collision_is_preflighted_without_constructing_factories() -> None:
    """Any existing core key is rejected before Runtime registers other keys."""
    services = ServiceContainer()
    constructions = 0

    def bus_factory(_: ServiceContainer) -> EventBus:
        nonlocal constructions
        constructions += 1
        return EventBus()

    services.register_factory(EventBus, bus_factory)
    settings = AgentOSSettings(environment="collision")
    with pytest.raises(ServiceError, match="EventBus"):
        Runtime(settings, EventBus(), Registry(), InMemoryTelemetrySink(), services=services)
    assert constructions == 0
    assert not services.contains(AgentOSSettings)
    assert services.contains(EventBus)


def test_component_registration_delegates_to_manager() -> None:
    """Runtime registration forwards the component and dependency names."""
    runtime = make_runtime()
    component = RuntimeProbe("worker")
    runtime.register_component(component, depends_on=("database",))
    assert runtime.component_manager.get("worker") is component
    assert runtime.component_manager.names() == ("worker",)


def test_legacy_start_remains_synchronous_and_does_not_start_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy start configures logging and emits its historical event only."""
    import agentos.runtime.runtime as runtime_module

    configured: list[str] = []
    monkeypatch.setattr(runtime_module, "configure_logging", configured.append)
    runtime = make_runtime()
    assert runtime.start() is None
    assert configured == ["WARNING"]
    assert runtime.state is LifecycleState.NEW
    events = tuple(runtime.telemetry.list())
    assert len(events) == 1
    assert events[0].name == "runtime.started"
    assert events[0].attributes == {"environment": "test"}


def test_legacy_start_preserves_ordinary_telemetry_error() -> None:
    """Legacy telemetry errors retain their historical propagation behavior."""
    error = RuntimeError("telemetry failed")
    runtime = make_runtime(telemetry=FaultyTelemetry(error, "runtime.started"))
    with pytest.raises(RuntimeError) as caught:
        runtime.start()
    assert caught.value is error
    assert runtime.state is LifecycleState.NEW


@pytest.mark.asyncio
async def test_managed_empty_lifecycle_and_telemetry_ordering() -> None:
    """Empty manager transitions emit one event after each real transition."""
    runtime = make_runtime()
    await runtime.initialize_async()
    await runtime.initialize_async()
    await runtime.start_async()
    await runtime.start_async()
    await runtime.stop_async()
    await runtime.stop_async()

    assert runtime.state is LifecycleState.STOPPED
    assert [event.name for event in runtime.telemetry.list()] == [
        "runtime.initialized",
        "runtime.started",
        "runtime.stopped",
    ]
    assert all(event.attributes == {"environment": "test"} for event in runtime.telemetry.list())


@pytest.mark.asyncio
async def test_dependency_order_and_state_delegation() -> None:
    """Runtime delegates dependency ordering and state to its manager."""
    calls: list[str] = []
    runtime = make_runtime()
    application, database = RuntimeProbe("application", calls), RuntimeProbe("database", calls)
    runtime.register_component(application, depends_on=("database",))
    runtime.register_component(database)
    await runtime.initialize_async()
    assert runtime.state is LifecycleState.INITIALIZED
    await runtime.start_async()
    assert runtime.state is LifecycleState.STARTED
    await runtime.stop_async()
    assert runtime.state is LifecycleState.STOPPED
    assert calls == [
        "initialize:database",
        "initialize:application",
        "start:database",
        "start:application",
        "stop:application",
        "stop:database",
    ]


@pytest.mark.asyncio
async def test_managed_start_does_not_initialize_automatically() -> None:
    """Start before initialize is rejected without invoking component hooks."""
    runtime = make_runtime()
    component = RuntimeProbe("worker")
    runtime.register_component(component)
    with pytest.raises(AgentOSRuntimeError, match="cannot start"):
        await runtime.start_async()
    assert component.calls == []
    assert runtime.state is LifecycleState.NEW


@pytest.mark.asyncio
async def test_legacy_start_is_rejected_after_managed_operation_begins() -> None:
    """The legacy signal cannot be emitted after managed lifecycle is requested."""
    runtime = make_runtime()
    with pytest.raises(AgentOSRuntimeError, match="cannot start"):
        await runtime.start_async()
    with pytest.raises(AgentOSRuntimeError, match=r"legacy Runtime.start"):
        runtime.start()
    assert runtime.state is LifecycleState.NEW
    assert tuple(runtime.telemetry.list()) == ()


@pytest.mark.asyncio
async def test_initialize_failure_preserves_primary_and_emits_failure_event() -> None:
    """Initialization errors propagate by identity after manager failure is set."""
    runtime = make_runtime()
    component = RuntimeProbe("worker")
    failure = RuntimeError("initialize failed")

    async def fail() -> None:
        raise failure

    component.initialize_hook = fail
    runtime.register_component(component)
    with pytest.raises(RuntimeError) as caught:
        await runtime.initialize_async()
    assert caught.value is failure
    assert runtime.state is LifecycleState.FAILED
    events = tuple(runtime.telemetry.list())
    assert [event.name for event in events] == ["runtime.lifecycle_failed"]
    assert events[0].attributes == {"environment": "test", "operation": "initialize"}


@pytest.mark.asyncio
async def test_start_failure_preserves_manager_exception_group() -> None:
    """Runtime propagates ComponentManager rollback groups unchanged."""
    runtime = make_runtime()
    component = RuntimeProbe("worker")
    primary = RuntimeError("start failed")

    async def fail_start() -> None:
        raise primary

    async def fail_stop() -> None:
        raise ValueError("cleanup failed")

    component.start_hook = fail_start
    component.stop_hook = fail_stop
    runtime.register_component(component)
    await runtime.initialize_async()
    with pytest.raises(ExceptionGroup) as caught:
        await runtime.start_async()
    assert caught.value.exceptions[0] is primary
    assert runtime.state is LifecycleState.FAILED
    assert [event.name for event in runtime.telemetry.list()] == [
        "runtime.initialized",
        "runtime.lifecycle_failed",
    ]


@pytest.mark.asyncio
async def test_failed_shutdown_emits_failure_and_retries_cleanup() -> None:
    """Failed stop leaves manager FAILED and a later stop completes cleanup."""
    runtime = make_runtime()
    component = RuntimeProbe("worker")
    failing = True

    async def cleanup() -> None:
        nonlocal failing
        if failing:
            raise RuntimeError("cleanup pending")

    component.stop_hook = cleanup
    runtime.register_component(component)
    await runtime.initialize_async()
    await runtime.start_async()
    with pytest.raises(ExceptionGroup):
        await runtime.stop_async()
    assert runtime.state is LifecycleState.FAILED
    failing = False
    await runtime.stop_async()
    assert runtime.state is LifecycleState.STOPPED
    assert [event.name for event in runtime.telemetry.list()] == [
        "runtime.initialized",
        "runtime.started",
        "runtime.lifecycle_failed",
        "runtime.stopped",
    ]


@pytest.mark.asyncio
async def test_ordinary_managed_telemetry_failures_do_not_change_lifecycle() -> None:
    """Ordinary telemetry faults do not replace managed lifecycle outcomes."""
    telemetry = FaultyTelemetry(RuntimeError("diagnostic fault"), "runtime.started")
    runtime = make_runtime(telemetry=telemetry)
    await runtime.initialize_async()
    await runtime.start_async()
    assert runtime.state is LifecycleState.STARTED
    assert [event.name for event in telemetry.list()] == ["runtime.initialized"]


@pytest.mark.asyncio
async def test_control_flow_telemetry_error_propagates_after_transition() -> None:
    """Telemetry control-flow exceptions escape after manager state changes."""
    control = KeyboardInterrupt("telemetry interrupted")
    runtime = make_runtime(telemetry=FaultyTelemetry(control, "runtime.started"))
    await runtime.initialize_async()
    with pytest.raises(KeyboardInterrupt) as caught:
        await runtime.start_async()
    assert caught.value is control
    assert runtime.state is LifecycleState.STARTED


@pytest.mark.asyncio
async def test_lifecycle_does_not_publish_events_on_event_bus() -> None:
    """Managed telemetry does not cause implicit EventBus lifecycle publication."""
    runtime = make_runtime()
    seen: list[Event] = []

    async def capture(event: Event) -> None:
        seen.append(event)

    for name in ("runtime.initialized", "runtime.started", "runtime.stopped"):
        runtime.event_bus.subscribe(name, capture)
    await runtime.initialize_async()
    await runtime.start_async()
    await runtime.stop_async()
    assert seen == []


@pytest.mark.asyncio
async def test_cancellation_propagates_and_sets_manager_failed() -> None:
    """Lifecycle cancellation keeps identity and settles failure telemetry."""
    runtime = make_runtime()
    component = RuntimeProbe("worker")
    expected = asyncio.CancelledError("cancel startup")

    async def cancel() -> None:
        raise expected

    component.start_hook = cancel
    runtime.register_component(component)
    await runtime.initialize_async()
    with pytest.raises(asyncio.CancelledError) as caught:
        await runtime.start_async()
    assert caught.value is expected
    assert runtime.state is LifecycleState.FAILED
    assert tuple(event.name for event in runtime.telemetry.list())[-1] == "runtime.lifecycle_failed"


@pytest.mark.parametrize("control_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.asyncio
async def test_process_control_propagates_from_component_hook(
    control_type: type[BaseException],
) -> None:
    """Component process-control exceptions retain identity after failure reporting."""
    runtime = make_runtime()
    component = RuntimeProbe("worker")
    expected = control_type("stop process")

    async def interrupt() -> None:
        raise expected

    component.start_hook = interrupt
    runtime.register_component(component)
    await runtime.initialize_async()
    with pytest.raises(control_type) as caught:
        await runtime.start_async()
    assert caught.value is expected
    assert runtime.state is LifecycleState.FAILED
    assert tuple(event.name for event in runtime.telemetry.list())[-1] == "runtime.lifecycle_failed"


@pytest.mark.asyncio
async def test_ordinary_failure_telemetry_error_does_not_replace_lifecycle_error() -> None:
    """Failure reporting faults cannot replace the original ordinary exception."""
    primary = RuntimeError("component startup failed")
    telemetry_error = ValueError("failure telemetry broke")
    runtime = make_runtime(telemetry=FaultyTelemetry(telemetry_error, "runtime.lifecycle_failed"))
    component = RuntimeProbe("worker")

    async def fail() -> None:
        raise primary

    component.start_hook = fail
    runtime.register_component(component)
    await runtime.initialize_async()
    with pytest.raises(RuntimeError) as caught:
        await runtime.start_async()
    assert caught.value is primary
    assert runtime.state is LifecycleState.FAILED


@pytest.mark.asyncio
async def test_control_flow_failure_telemetry_exception_is_not_suppressed() -> None:
    """Telemetry control flow escapes with the lifecycle failure as context."""
    primary = RuntimeError("component startup failed")
    telemetry_control = KeyboardInterrupt("failure telemetry interrupted")
    runtime = make_runtime(telemetry=FaultyTelemetry(telemetry_control, "runtime.lifecycle_failed"))
    component = RuntimeProbe("worker")

    async def fail() -> None:
        raise primary

    component.start_hook = fail
    runtime.register_component(component)
    await runtime.initialize_async()
    with pytest.raises(KeyboardInterrupt) as caught:
        await runtime.start_async()
    assert caught.value is telemetry_control
    assert telemetry_control.__context__ is primary
    assert runtime.state is LifecycleState.FAILED


@pytest.mark.asyncio
async def test_concurrent_managed_calls_are_serialized_without_duplicate_events() -> None:
    """Concurrent repeated initialization reports its transition only once."""
    runtime = make_runtime()
    lock = ObservableLock()
    runtime._lifecycle_lock = lock
    entered, release = asyncio.Event(), asyncio.Event()
    component = RuntimeProbe("worker")

    async def block() -> None:
        entered.set()
        await release.wait()

    component.initialize_hook = block
    runtime.register_component(component)
    first = asyncio.create_task(runtime.initialize_async())
    await wait_for(entered)
    second = asyncio.create_task(runtime.initialize_async())
    await wait_for(lock.waiting)
    release.set()
    await asyncio.gather(first, second)
    assert runtime.state is LifecycleState.INITIALIZED
    assert tuple(event.name for event in runtime.telemetry.list()) == ("runtime.initialized",)


class ObservableLock(asyncio.Lock):
    """Lock that signals queued callers without timing sleeps."""

    def __init__(self) -> None:
        """Create a lock with a waiter signal."""
        super().__init__()
        self.waiting = asyncio.Event()

    async def acquire(self) -> bool:
        """Signal a queued acquire before waiting."""
        if self.locked():
            self.waiting.set()
        return await super().acquire()


@pytest.mark.asyncio
async def test_cancelled_waiter_does_not_change_runtime_manager_state() -> None:
    """Cancellation while queued on Runtime synchronization has no state effect."""
    runtime = make_runtime()
    lock = ObservableLock()
    runtime._lifecycle_lock = lock
    entered, release = asyncio.Event(), asyncio.Event()
    component = RuntimeProbe("worker")

    async def block() -> None:
        entered.set()
        await release.wait()

    component.initialize_hook = block
    runtime.register_component(component)
    owner = asyncio.create_task(runtime.initialize_async())
    await wait_for(entered)
    waiter = asyncio.create_task(runtime.initialize_async())
    await wait_for(lock.waiting)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter
    assert runtime.state is LifecycleState.NEW
    release.set()
    await owner
    assert runtime.state is LifecycleState.INITIALIZED


@pytest.mark.asyncio
async def test_same_task_runtime_reentrancy_fails_without_deadlock() -> None:
    """A component hook cannot recursively enter Runtime lifecycle methods."""
    runtime = make_runtime()
    component = RuntimeProbe("worker")

    async def recurse() -> None:
        await runtime.stop_async()

    component.initialize_hook = recurse
    runtime.register_component(component)
    with pytest.raises(AgentOSRuntimeError, match="recursively"):
        await asyncio.wait_for(runtime.initialize_async(), timeout=2)
    assert runtime.state is LifecycleState.FAILED


@pytest.mark.asyncio
async def test_managed_stop_does_not_drain_in_flight_agent_execution() -> None:
    """An admitted BaseAgent run may finish after Runtime managed shutdown."""
    entered, release = asyncio.Event(), asyncio.Event()

    class WaitingAgent(BaseAgent[AgentContext, AgentResult]):
        async def _execute(self, context: AgentContext) -> AgentResult:
            entered.set()
            await release.wait()
            return AgentResult(content=context.goal)

    runtime = make_runtime()
    agent = WaitingAgent("waiting")
    runtime.register_component(agent)
    await runtime.initialize_async()
    await runtime.start_async()
    run = asyncio.create_task(agent.run(AgentContext(goal="complete")))
    await wait_for(entered)
    await runtime.stop_async()
    assert runtime.state is LifecycleState.STOPPED
    release.set()
    assert (await run).content == "complete"
