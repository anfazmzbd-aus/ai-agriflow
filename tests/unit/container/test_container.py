from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Literal, Protocol, cast

import pytest

from agentos.base import LifecycleComponent, LifecycleState, ServiceError
from agentos.container import ServiceContainer


class Store(Protocol):
    """Storage interface used to verify Protocol service keys."""

    def read(self) -> str:
        """Return stored text."""


class MemoryStore:
    """Concrete in-memory implementation of Store."""

    def read(self) -> str:
        """Return a stable test value."""
        return "stored"


class AbstractClock(ABC):
    """Abstract service key used in container tests."""

    @abstractmethod
    def now(self) -> int:
        """Return a test timestamp."""


class FixedClock(AbstractClock):
    """Concrete clock used by the abstract-key test."""

    def now(self) -> int:
        """Return the fixed test timestamp."""
        return 123


def test_instance_registration_preserves_identity_and_contains() -> None:
    """Registered instances retain identity and appear in contains()."""
    container = ServiceContainer()
    instance = MemoryStore()

    assert container.contains(MemoryStore) is False
    container.register_instance(MemoryStore, instance)

    assert container.contains(MemoryStore) is True
    assert container.resolve(MemoryStore) is instance


def test_duplicate_instance_and_factory_registration_are_rejected() -> None:
    """Each service key accepts only one registration."""
    container = ServiceContainer()
    container.register_instance(MemoryStore, MemoryStore())

    with pytest.raises(ServiceError, match="already registered"):
        container.register_instance(MemoryStore, MemoryStore())
    with pytest.raises(ServiceError, match="already registered"):
        container.register_factory(MemoryStore, lambda _: MemoryStore())


def test_invalid_keys_instances_factories_and_lifetimes_are_rejected() -> None:
    """Reject invalid class keys, None values, factories, and lifetimes."""
    container = ServiceContainer()
    invalid_key = cast(type[object], "service")
    invalid_factory = cast(Callable[[ServiceContainer], MemoryStore], 42)

    with pytest.raises(TypeError, match="class object"):
        container.register_instance(invalid_key, object())
    with pytest.raises(TypeError, match="class object"):
        container.resolve(invalid_key)
    with pytest.raises(TypeError, match="class object"):
        container.contains(cast(type[object], None))
    with pytest.raises(TypeError, match="cannot be None"):
        container.register_instance(MemoryStore, cast(MemoryStore, None))
    with pytest.raises(TypeError, match="callable"):
        container.register_factory(MemoryStore, invalid_factory)
    with pytest.raises(ValueError, match="lifetime"):
        container.register_factory(
            MemoryStore,
            lambda _: MemoryStore(),
            lifetime=cast(Literal["singleton", "transient"], "scoped"),
        )


def test_singleton_factory_is_lazy_and_cached() -> None:
    """Singleton creation is deferred and cached after its first resolution."""
    container = ServiceContainer()
    calls = 0

    def factory(_: ServiceContainer) -> MemoryStore:
        nonlocal calls
        calls += 1
        return MemoryStore()

    container.register_factory(MemoryStore, factory)

    assert container.contains(MemoryStore) is True
    assert calls == 0
    first = container.resolve(MemoryStore)
    second = container.resolve(MemoryStore)

    assert calls == 1
    assert first is second


def test_transient_factory_creates_a_new_instance_each_time() -> None:
    """Transient registrations construct a new instance for each resolution."""
    container = ServiceContainer()
    container.register_factory(
        MemoryStore,
        lambda _: MemoryStore(),
        lifetime="transient",
    )

    assert container.resolve(MemoryStore) is not container.resolve(MemoryStore)


def test_factories_can_resolve_a_multi_level_dependency_chain() -> None:
    """Factories can explicitly resolve their transitive dependencies."""

    class Repository:
        def __init__(self, store: Store) -> None:
            self.store = store

    class Service:
        def __init__(self, repository: Repository) -> None:
            self.repository = repository

    container = ServiceContainer()
    store_key = cast(type[Store], cast(object, Store))
    container.register_factory(store_key, lambda _: MemoryStore())
    container.register_factory(
        Repository,
        lambda services: Repository(services.resolve(store_key)),
    )
    container.register_factory(
        Service,
        lambda services: Service(services.resolve(Repository)),
    )

    assert container.resolve(Service).repository.store.read() == "stored"


def test_direct_cycle_reports_readable_dependency_path() -> None:
    """A direct recursive factory reports a readable dependency path."""

    class Direct:
        pass

    container = ServiceContainer()
    container.register_factory(Direct, lambda services: services.resolve(Direct))

    with pytest.raises(ServiceError, match=r"Direct.*Direct"):
        container.resolve(Direct)


def test_indirect_cycle_reports_complete_dependency_path() -> None:
    """An indirect cycle reports each service key in dependency order."""

    class First:
        pass

    class Second:
        pass

    class Third:
        pass

    container = ServiceContainer()
    container.register_factory(
        First,
        lambda services: cast(First, services.resolve(Second)),
    )
    container.register_factory(
        Second,
        lambda services: cast(Second, services.resolve(Third)),
    )
    container.register_factory(
        Third,
        lambda services: cast(Third, services.resolve(First)),
    )

    with pytest.raises(ServiceError) as captured:
        container.resolve(First)

    message = str(captured.value)
    assert message.index("First") < message.index("Second") < message.index("Third")
    assert message.endswith("First")


def test_missing_service_raises_service_error() -> None:
    """Resolving an unregistered class key raises ServiceError."""
    with pytest.raises(ServiceError, match="not registered"):
        ServiceContainer().resolve(MemoryStore)


def test_factory_exception_identity_traceback_and_stack_cleanup() -> None:
    """Factory exceptions propagate unchanged and failed paths are cleared."""

    class Flaky:
        pass

    container = ServiceContainer()
    expected = RuntimeError("factory failed")
    calls = 0

    def factory(services: ServiceContainer) -> Flaky:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise expected
        return Flaky()

    container.register_factory(Flaky, factory)

    with pytest.raises(RuntimeError) as captured:
        container.resolve(Flaky)

    assert captured.value is expected
    traceback = captured.value.__traceback__
    frame_names: list[str] = []
    while traceback is not None:
        frame_names.append(traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    assert "factory" in frame_names
    assert container.resolve(Flaky) is not None


def test_failed_singleton_construction_can_be_retried() -> None:
    """A failed lazy singleton is not cached and can succeed on retry."""

    class Retryable:
        pass

    container = ServiceContainer()
    calls = 0

    def factory(_: ServiceContainer) -> Retryable:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("try again")
        return Retryable()

    container.register_factory(Retryable, factory)

    with pytest.raises(RuntimeError, match="try again"):
        container.resolve(Retryable)
    result = container.resolve(Retryable)

    assert isinstance(result, Retryable)
    assert calls == 2
    assert container.resolve(Retryable) is result


def test_factory_returning_none_fails_without_caching() -> None:
    """None factory results fail and are not cached."""

    class MissingValue:
        pass

    container = ServiceContainer()
    calls = 0

    def factory(_: ServiceContainer) -> MissingValue:
        nonlocal calls
        calls += 1
        return cast(MissingValue, None)

    container.register_factory(MissingValue, factory)

    for _ in range(2):
        with pytest.raises(ServiceError, match="returned None"):
            container.resolve(MissingValue)

    assert calls == 2


def test_protocol_and_abstract_class_keys_preserve_static_types() -> None:
    """Protocol and abstract keys resolve to their declared interface types."""
    container = ServiceContainer()
    store_key = cast(type[Store], cast(object, Store))
    clock_key = cast(type[AbstractClock], cast(object, AbstractClock))
    container.register_instance(store_key, MemoryStore())
    container.register_factory(clock_key, lambda _: FixedClock())

    store: Store = container.resolve(store_key)
    clock: AbstractClock = container.resolve(clock_key)

    assert store.read() == "stored"
    assert clock.now() == 123


def test_awaitable_factory_results_are_rejected_and_coroutine_is_closed() -> None:
    """An async factory result is closed and rejected as unsupported."""

    class AsyncService:
        pass

    container = ServiceContainer()

    async def factory(_: ServiceContainer) -> AsyncService:
        return AsyncService()

    container.register_factory(
        AsyncService,
        cast(Callable[[ServiceContainer], AsyncService], factory),
    )

    with pytest.raises(ServiceError, match="async service construction is unsupported"):
        container.resolve(AsyncService)


@pytest.mark.asyncio
async def test_non_coroutine_awaitable_factory_result_is_rejected() -> None:
    """Future-like factory results are rejected without coroutine cleanup."""

    class FutureService:
        pass

    container = ServiceContainer()
    future = asyncio.get_running_loop().create_future()
    container.register_factory(
        FutureService,
        lambda _: cast(FutureService, future),
    )

    with pytest.raises(ServiceError, match="async service construction is unsupported"):
        container.resolve(FutureService)


def test_concurrent_singleton_resolution_constructs_once() -> None:
    """Concurrent callers share one successfully created singleton."""

    class Shared:
        pass

    container = ServiceContainer()
    construction_count = 0

    def factory(_: ServiceContainer) -> Shared:
        nonlocal construction_count
        construction_count += 1
        return Shared()

    container.register_factory(Shared, factory)
    workers = 6
    ready = Barrier(workers + 1)

    def resolve_after_ready() -> Shared:
        ready.wait()
        return container.resolve(Shared)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(resolve_after_ready) for _ in range(workers)]
        ready.wait()
        results = [future.result() for future in futures]

    assert construction_count == 1
    assert all(result is results[0] for result in results)


def test_containers_are_isolated() -> None:
    """Each container owns an independent registration set."""
    first = ServiceContainer()
    second = ServiceContainer()
    first.register_instance(MemoryStore, MemoryStore())

    assert first.contains(MemoryStore)
    assert not second.contains(MemoryStore)
    with pytest.raises(ServiceError):
        second.resolve(MemoryStore)


def test_resolving_lifecycle_component_does_not_run_lifecycle_hooks() -> None:
    """Resolution does not initialize, start, or stop a lifecycle component."""

    class Managed(LifecycleComponent):
        def __init__(self) -> None:
            super().__init__("managed")
            self.hooks_called = 0

        async def _initialize(self) -> None:
            self.hooks_called += 1

        async def _start(self) -> None:
            self.hooks_called += 1

        async def _stop(self) -> None:
            self.hooks_called += 1

    container = ServiceContainer()
    container.register_factory(Managed, lambda _: Managed())

    service = container.resolve(Managed)

    assert service.lifecycle_state is LifecycleState.NEW
    assert service.hooks_called == 0


def test_registry_and_runtime_remain_independent_and_compatible() -> None:
    """The existing registry and runtime remain usable without integration."""
    from agentos.core.config import AgentOSSettings
    from agentos.registry import Registry
    from agentos.runtime import Runtime

    registry = Registry[int]()
    registry.register("answer", 42)
    runtime = Runtime.from_settings(AgentOSSettings(environment="test"))

    assert registry.get("answer") == 42
    assert isinstance(runtime.registry, Registry)
