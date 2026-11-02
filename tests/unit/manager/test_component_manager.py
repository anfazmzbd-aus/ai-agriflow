"""Tests for the asynchronous component lifecycle manager."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from agentos.base import (
    AgentOSRuntimeError,
    ConfigurationError,
    LifecycleComponent,
    LifecycleState,
    RegistrationError,
)
from agentos.manager import ComponentManager

Hook = Callable[[], Awaitable[None]]


class Probe(LifecycleComponent):
    """Lifecycle component that records and controls its hooks."""

    def __init__(self, name: str, calls: list[str] | None = None) -> None:
        """Exercise   init  ."""
        super().__init__(name)
        self.calls = calls if calls is not None else []
        self.initialize_hook: Hook | None = None
        self.start_hook: Hook | None = None
        self.stop_hook: Hook | None = None

    async def _initialize(self) -> None:
        self.calls.append(f"initialize:{self.name}")
        if self.initialize_hook:
            await self.initialize_hook()

    async def _start(self) -> None:
        self.calls.append(f"start:{self.name}")
        if self.start_hook:
            await self.start_hook()

    async def _stop(self) -> None:
        self.calls.append(f"stop:{self.name}")
        if self.stop_hook:
            await self.stop_hook()


async def signal(event: asyncio.Event) -> None:
    """Wait with a bound to make synchronization failures actionable."""
    await asyncio.wait_for(event.wait(), timeout=2)


@pytest.fixture
def manager() -> ComponentManager:
    """Exercise manager."""
    return ComponentManager()


def test_register_lookup_names_and_public_export(manager: ComponentManager) -> None:
    """Exercise test register lookup names and public export."""
    first = Probe("first")
    second = Probe("second")
    manager.register(first)
    manager.register(second)

    assert manager.get("first") is first
    assert manager.names() == ("first", "second")
    assert manager.state is LifecycleState.NEW
    with pytest.raises(RegistrationError, match="not registered"):
        manager.get("missing")


def test_duplicate_names_and_component_identity_are_rejected(manager: ComponentManager) -> None:
    """Exercise test duplicate names and component identity are rejected."""
    component = Probe("same")
    manager.register(component)
    with pytest.raises(RegistrationError):
        manager.register(Probe("same"))
    with pytest.raises(RegistrationError, match="object"):
        manager.register(component, depends_on=("alternate",))


def test_registration_rejects_wrong_component_type_and_malformed_dependencies() -> None:
    """Invalid component objects and malformed dependency entries fail early."""
    manager = ComponentManager()
    with pytest.raises(TypeError, match="LifecycleComponent"):
        manager.register(object())  # type: ignore[arg-type]
    with pytest.raises(ConfigurationError, match="non-empty strings"):
        manager.register(Probe("consumer"), depends_on=("",))
    with pytest.raises(ConfigurationError, match="non-empty strings"):
        manager.register(Probe("consumer"), depends_on=(None,))  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_missing_and_self_dependencies_are_config_errors() -> None:
    """Exercise test missing and self dependencies are config errors."""
    manager = ComponentManager()
    manager.register(Probe("consumer"), depends_on=("missing",))
    with pytest.raises(ConfigurationError, match="missing dependencies"):
        await manager.initialize()
    assert manager.state is LifecycleState.NEW

    with pytest.raises(ConfigurationError, match="depend on itself"):
        ComponentManager().register(Probe("self"), depends_on=("self",))


def test_duplicate_dependency_declarations_are_rejected() -> None:
    """Exercise test duplicate dependency declarations are rejected."""
    manager = ComponentManager()
    with pytest.raises(ConfigurationError, match="duplicate dependencies"):
        manager.register(Probe("consumer"), depends_on=("db", "db"))


def test_forward_references_and_stable_topological_order() -> None:
    """Exercise test forward references and stable topological order."""
    calls: list[str] = []
    manager = ComponentManager()
    manager.register(Probe("application", calls), depends_on=("database",))
    manager.register(Probe("metrics", calls))
    manager.register(Probe("database", calls))
    manager.register(Probe("cache", calls))

    async def run() -> None:
        await manager.initialize()
        await manager.start()

    asyncio.run(run())
    assert [call for call in calls if call.startswith("initialize:")] == [
        "initialize:metrics",
        "initialize:database",
        "initialize:application",
        "initialize:cache",
    ]
    assert [call for call in calls if call.startswith("start:")] == [
        "start:metrics",
        "start:database",
        "start:application",
        "start:cache",
    ]


@pytest.mark.asyncio
async def test_cycle_has_readable_diagnostic_before_hooks() -> None:
    """Exercise test cycle has readable diagnostic before hooks."""
    manager = ComponentManager()
    a, b, c = Probe("a"), Probe("b"), Probe("c")
    manager.register(a, depends_on=("c",))
    manager.register(b, depends_on=("a",))
    manager.register(c, depends_on=("b",))
    with pytest.raises(ConfigurationError, match=r"a -> c -> b -> a"):
        await manager.initialize()
    assert not a.calls + b.calls + c.calls
    assert manager.state is LifecycleState.NEW


@pytest.mark.asyncio
async def test_cycle_diagnostic_with_shared_and_independent_dependencies() -> None:
    """Cycle search propagates through a longer cycle beside shared dependencies."""
    manager = ComponentManager()
    manager.register(Probe("root"), depends_on=("left", "right"))
    manager.register(Probe("left"), depends_on=("shared", "cycle-a"))
    manager.register(Probe("right"), depends_on=("shared", "cycle-a"))
    manager.register(Probe("shared"), depends_on=("cycle-a",))
    manager.register(Probe("cycle-a"), depends_on=("cycle-b",))
    manager.register(Probe("cycle-b"), depends_on=("cycle-c",))
    manager.register(Probe("cycle-c"), depends_on=("cycle-a",))
    manager.register(Probe("independent"))

    with pytest.raises(
        ConfigurationError,
        match=r"cycle-a -> cycle-b -> cycle-c -> cycle-a",
    ):
        await manager.initialize()

    assert all(manager.get(name).lifecycle_state is LifecycleState.NEW for name in manager.names())
    assert manager.state is LifecycleState.NEW


@pytest.mark.asyncio
async def test_preflight_checks_every_component_before_running_hooks() -> None:
    """Exercise test preflight checks every component before running hooks."""
    manager = ComponentManager()
    first, second = Probe("first"), Probe("second")
    await second.initialize()
    manager.register(first)
    manager.register(second)

    with pytest.raises(ConfigurationError, match="must be NEW"):
        await manager.initialize()

    assert first.calls == []
    assert first.lifecycle_state is LifecycleState.NEW
    assert manager.state is LifecycleState.NEW
    manager.register(Probe("third"))


@pytest.mark.asyncio
async def test_all_initialization_finishes_before_any_start() -> None:
    """Exercise test all initialization finishes before any start."""
    calls: list[str] = []
    manager = ComponentManager()
    manager.register(Probe("one", calls))
    manager.register(Probe("two", calls))
    await manager.initialize()
    await manager.start()
    assert calls == [
        "initialize:one",
        "initialize:two",
        "start:one",
        "start:two",
    ]


@pytest.mark.asyncio
async def test_lifecycle_idempotency_invalid_transitions_and_terminal_stop() -> None:
    """Exercise test lifecycle idempotency invalid transitions and terminal stop."""
    manager = ComponentManager()
    manager.register(Probe("one"))
    with pytest.raises(AgentOSRuntimeError, match="cannot start"):
        await manager.start()
    await manager.initialize()
    await manager.initialize()
    await manager.start()
    await manager.start()
    await manager.stop()
    await manager.stop()
    assert manager.state is LifecycleState.STOPPED
    with pytest.raises(AgentOSRuntimeError, match="cannot initialize"):
        await manager.initialize()
    with pytest.raises(AgentOSRuntimeError, match="cannot start"):
        await manager.start()


@pytest.mark.asyncio
async def test_stop_from_new_stops_components_without_hooks() -> None:
    """Exercise test stop from new stops components without hooks."""
    manager = ComponentManager()
    one, two = Probe("one"), Probe("two")
    manager.register(one)
    manager.register(two)
    await manager.stop()
    assert manager.state is LifecycleState.STOPPED
    assert one.lifecycle_state is two.lifecycle_state is LifecycleState.STOPPED
    assert one.calls == two.calls == []


@pytest.mark.asyncio
async def test_stop_uses_reverse_topological_order() -> None:
    """Exercise test stop uses reverse topological order."""
    calls: list[str] = []
    manager = ComponentManager()
    manager.register(Probe("app", calls), depends_on=("db",))
    manager.register(Probe("db", calls))
    manager.register(Probe("metrics", calls))
    await manager.initialize()
    await manager.start()
    calls.clear()
    await manager.stop()
    assert calls == ["stop:metrics", "stop:app", "stop:db"]


@pytest.mark.asyncio
async def test_initialization_failure_rolls_back_attempted_in_reverse_order() -> None:
    """Exercise test initialization failure rolls back attempted in reverse order."""
    calls: list[str] = []
    manager = ComponentManager()
    one, two, three = (Probe(name, calls) for name in ("one", "two", "three"))
    manager.register(one)
    manager.register(two)
    manager.register(three)
    failure = RuntimeError("initialization failed")

    async def fail() -> None:
        raise failure

    two.initialize_hook = fail
    with pytest.raises(RuntimeError) as caught:
        await manager.initialize()
    assert caught.value is failure
    assert calls == [
        "initialize:one",
        "initialize:two",
        "stop:two",
        "stop:one",
    ]
    assert manager.state is LifecycleState.FAILED


@pytest.mark.asyncio
async def test_start_failure_rolls_back_every_initialized_component() -> None:
    """Exercise test start failure rolls back every initialized component."""
    calls: list[str] = []
    manager = ComponentManager()
    one, two = Probe("one", calls), Probe("two", calls)
    manager.register(one)
    manager.register(two)
    await manager.initialize()

    async def fail() -> None:
        raise RuntimeError("start broke")

    two.start_hook = fail
    with pytest.raises(RuntimeError, match="start broke"):
        await manager.start()
    assert calls[-2:] == ["stop:two", "stop:one"]
    assert manager.state is LifecycleState.FAILED


@pytest.mark.asyncio
async def test_rollback_aggregates_primary_and_cleanup_failures() -> None:
    """Exercise test rollback aggregates primary and cleanup failures."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)
    primary = RuntimeError("start primary")

    async def fail_start() -> None:
        raise primary

    async def fail_stop() -> None:
        raise ValueError("cleanup failed")

    component.start_hook = fail_start
    component.stop_hook = fail_stop
    await manager.initialize()
    with pytest.raises(ExceptionGroup) as caught:
        await manager.start()
    assert caught.value.exceptions[0] is primary
    assert isinstance(caught.value.exceptions[1], ValueError)
    assert manager.state is LifecycleState.FAILED


@pytest.mark.asyncio
async def test_shutdown_continues_and_retry_finishes_failed_cleanup() -> None:
    """Exercise test shutdown continues and retry finishes failed cleanup."""
    calls: list[str] = []
    manager = ComponentManager()
    one, two = Probe("one", calls), Probe("two", calls)
    manager.register(one)
    manager.register(two)
    await manager.initialize()
    await manager.start()
    fail = True

    async def flaky_cleanup() -> None:
        nonlocal fail
        if fail:
            raise RuntimeError("not yet")

    two.stop_hook = flaky_cleanup
    with pytest.raises(ExceptionGroup) as caught:
        await manager.stop()
    assert len(caught.value.exceptions) == 1
    assert calls[-2:] == ["stop:two", "stop:one"]
    assert manager.state is LifecycleState.FAILED
    fail = False
    await manager.stop()
    assert manager.state is LifecycleState.STOPPED
    assert two.calls.count("stop:two") == 2


@pytest.mark.asyncio
async def test_process_control_failure_propagates_and_cleanup_is_attempted() -> None:
    """Exercise test process control failure propagates and cleanup is attempted."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)
    expected = KeyboardInterrupt("stop now")

    async def interrupt() -> None:
        raise expected

    component.initialize_hook = interrupt
    with pytest.raises(KeyboardInterrupt) as caught:
        await manager.initialize()
    assert caught.value is expected
    # LifecycleComponent intentionally treats stop() from NEW as a no-op for hooks.
    assert component.calls == ["initialize:one"]
    assert manager.state is LifecycleState.FAILED


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.asyncio
async def test_process_control_in_start_propagates_unchanged(
    exception_type: type[BaseException],
) -> None:
    """Exercise test process control in start propagates unchanged."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)
    await manager.initialize()
    expected = exception_type("control")

    async def interrupt() -> None:
        raise expected

    component.start_hook = interrupt
    with pytest.raises(exception_type) as caught:
        await manager.start()
    assert caught.value is expected
    assert manager.state is LifecycleState.FAILED


@pytest.mark.parametrize("operation", ["initialize", "start", "stop"])
@pytest.mark.asyncio
async def test_cancellation_during_hook_is_preserved_and_cleanup_attempted(operation: str) -> None:
    """Exercise test cancellation during hook is preserved and cleanup attempted."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)
    if operation != "initialize":
        await manager.initialize()
    if operation == "stop":
        await manager.start()
    entered, release = asyncio.Event(), asyncio.Event()

    async def block() -> None:
        entered.set()
        await release.wait()

    setattr(component, f"{operation}_hook", block)
    task = asyncio.create_task(getattr(manager, operation)())
    await signal(entered)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert manager.state is LifecycleState.FAILED
    if operation != "stop":
        assert component.lifecycle_state is LifecycleState.STOPPED


@pytest.mark.asyncio
async def test_cancelled_shutdown_cleanup_can_be_retried() -> None:
    """A later stop retries cleanup interrupted by cancellation."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)
    await manager.initialize()
    await manager.start()
    entered, release = asyncio.Event(), asyncio.Event()
    first_call = True

    async def interrupt_once() -> None:
        nonlocal first_call
        if first_call:
            first_call = False
            entered.set()
            await release.wait()

    component.stop_hook = interrupt_once
    task = asyncio.create_task(manager.stop())
    await signal(entered)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert manager.state is LifecycleState.FAILED
    await manager.stop()
    assert manager.state is LifecycleState.STOPPED
    assert component.lifecycle_state is LifecycleState.STOPPED


@pytest.mark.parametrize("control_type", [KeyboardInterrupt, SystemExit, asyncio.CancelledError])
@pytest.mark.asyncio
async def test_cleanup_control_exception_chains_startup_failure_and_can_retry(
    control_type: type[BaseException],
) -> None:
    """Cleanup control flow takes precedence and explicitly chains startup failure."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)
    await manager.initialize()
    primary = RuntimeError("startup operation failed")
    control = control_type("cleanup interrupted")
    fail_cleanup = True

    async def fail_start() -> None:
        raise primary

    async def fail_cleanup_once() -> None:
        nonlocal fail_cleanup
        if fail_cleanup:
            raise control

    component.start_hook = fail_start
    component.stop_hook = fail_cleanup_once
    with pytest.raises(control_type) as caught:
        await manager.start()

    assert caught.value is control
    assert control.__cause__ is primary
    assert control.__traceback__ is not None
    assert any("startup rollback" in note for note in control.__notes__)
    assert not isinstance(control, ExceptionGroup)
    assert manager.state is LifecycleState.FAILED
    assert component.lifecycle_state is LifecycleState.FAILED

    fail_cleanup = False
    await manager.stop()
    assert manager.state is LifecycleState.STOPPED
    assert component.lifecycle_state is LifecycleState.STOPPED


@pytest.mark.parametrize(
    ("primary_type", "control_message"),
    [
        (asyncio.CancelledError, "cancelled"),
        (KeyboardInterrupt, "interrupted"),
        (SystemExit, "exiting"),
    ],
)
@pytest.mark.asyncio
async def test_primary_control_exception_survives_ordinary_cleanup_failure(
    primary_type: type[BaseException], control_message: str
) -> None:
    """Primary control flow is re-raised with safe cleanup notes and retry state."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)
    await manager.initialize()
    primary = primary_type(control_message)
    existing_cause = LookupError("existing cause")
    primary.__cause__ = existing_cause
    cleanup_error = RuntimeError("cleanup detail that must not be copied")
    fail_cleanup = True

    async def fail_start() -> None:
        raise primary

    async def fail_cleanup_once() -> None:
        nonlocal fail_cleanup
        if fail_cleanup:
            raise cleanup_error

    component.start_hook = fail_start
    component.stop_hook = fail_cleanup_once
    with pytest.raises(primary_type) as caught:
        await manager.start()

    assert caught.value is primary
    assert primary.__cause__ is existing_cause
    assert any("RuntimeError" in note for note in primary.__notes__)
    assert all(str(cleanup_error) not in note for note in primary.__notes__)
    assert manager.state is LifecycleState.FAILED
    assert component.lifecycle_state is LifecycleState.FAILED

    fail_cleanup = False
    await manager.stop()
    assert manager.state is LifecycleState.STOPPED
    assert component.lifecycle_state is LifecycleState.STOPPED


class ObservableLock(asyncio.Lock):
    """Async lock that signals a contending acquisition without timing sleeps."""

    def __init__(self) -> None:
        """Exercise   init  ."""
        super().__init__()
        self.waiting = asyncio.Event()

    async def acquire(self) -> bool:
        """Exercise acquire."""
        if self.locked():
            self.waiting.set()
        return await super().acquire()


@pytest.mark.asyncio
async def test_cancellation_while_waiting_for_manager_lock_has_no_state_effect() -> None:
    """Exercise test cancellation while waiting for manager lock has no state effect."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)
    lock = ObservableLock()
    manager._lock = lock
    entered, release = asyncio.Event(), asyncio.Event()

    async def block() -> None:
        entered.set()
        await release.wait()

    component.initialize_hook = block
    first = asyncio.create_task(manager.initialize())
    await signal(entered)
    waiting = asyncio.create_task(manager.initialize())
    await signal(lock.waiting)
    waiting.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiting
    assert manager.state is LifecycleState.NEW
    release.set()
    await first
    assert manager.state is LifecycleState.INITIALIZED


@pytest.mark.asyncio
async def test_concurrent_lifecycle_calls_are_serialized_and_idempotent() -> None:
    """Exercise test concurrent lifecycle calls are serialized and idempotent."""
    calls: list[str] = []
    manager = ComponentManager()
    manager.register(Probe("one", calls))
    await asyncio.gather(manager.initialize(), manager.initialize())
    await asyncio.gather(manager.start(), manager.start())
    await asyncio.gather(manager.stop(), manager.stop())
    assert calls == ["initialize:one", "start:one", "stop:one"]
    assert manager.state is LifecycleState.STOPPED


@pytest.mark.asyncio
async def test_registration_rejected_while_hook_is_awaiting() -> None:
    """Exercise test registration rejected while hook is awaiting."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)
    entered, release = asyncio.Event(), asyncio.Event()

    async def block() -> None:
        entered.set()
        await release.wait()

    component.initialize_hook = block
    task = asyncio.create_task(manager.initialize())
    await signal(entered)
    with pytest.raises(AgentOSRuntimeError, match="register"):
        manager.register(Probe("late"))
    release.set()
    await task


@pytest.mark.asyncio
async def test_same_task_reentrancy_fails_without_deadlock() -> None:
    """Exercise test same task reentrancy fails without deadlock."""
    manager = ComponentManager()
    component = Probe("one")
    manager.register(component)

    async def recurse() -> None:
        await manager.stop()

    component.initialize_hook = recurse
    with pytest.raises(AgentOSRuntimeError, match="recursively"):
        await asyncio.wait_for(manager.initialize(), timeout=2)
    assert manager.state is LifecycleState.FAILED


@pytest.mark.asyncio
async def test_runtime_registry_and_base_agent_boundaries_remain_independent() -> None:
    """Exercise test runtime registry and base agent boundaries remain independent."""
    from agentos.agents import EchoAgent
    from agentos.runtime import Runtime

    manager = ComponentManager()
    component = Probe("managed")
    manager.register(component)
    runtime = Runtime.from_settings()
    await manager.initialize()
    await manager.start()
    assert tuple(runtime.registry.names()) == ()
    assert isinstance(EchoAgent(), object)
    assert not hasattr(manager, "event_bus")
    assert not hasattr(manager, "service_container")
    assert not hasattr(runtime, "component_manager")
    assert component.lifecycle_state is LifecycleState.STARTED


@pytest.mark.asyncio
async def test_base_agent_in_flight_run_may_finish_after_manager_stop() -> None:
    """Exercise test base agent in flight run may finish after manager stop."""
    from agentos.agents import AgentContext, AgentResult, BaseAgent

    entered, release = asyncio.Event(), asyncio.Event()

    class WaitingAgent(BaseAgent[AgentContext, AgentResult]):
        async def _execute(self, context: AgentContext) -> AgentResult:
            entered.set()
            await release.wait()
            return AgentResult(content=context.goal)

    manager = ComponentManager()
    agent = WaitingAgent("waiting-agent")
    manager.register(agent)
    await manager.initialize()
    await manager.start()
    run = asyncio.create_task(agent.run(AgentContext(goal="finished")))
    await signal(entered)
    await manager.stop()
    assert agent.lifecycle_state is LifecycleState.STOPPED
    release.set()
    assert (await run).content == "finished"
