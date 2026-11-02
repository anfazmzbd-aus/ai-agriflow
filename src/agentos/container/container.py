"""Typed, synchronous dependency registration and resolution."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from threading import RLock, local
from typing import Literal, cast

from agentos.base.exceptions import ServiceError

type ServiceFactory[ServiceT] = Callable[[ServiceContainer], ServiceT]
type ServiceLifetime = Literal["singleton", "transient"]


class _FactoryRegistration[ServiceT]:
    """Internal factory record with optional singleton cache state."""

    def __init__(self, factory: ServiceFactory[ServiceT], lifetime: ServiceLifetime) -> None:
        self.factory = factory
        self.lifetime = lifetime
        self.instance: ServiceT | None = None
        self.has_instance = False


class ServiceContainer:
    """Resolve explicitly registered services using class objects as keys.

    Resolution is synchronous and protected by a per-container reentrant lock.
    Singleton factories are lazy and cached after successful construction. Factory
    calls run while holding the lock, so unrelated resolutions are serialized.
    Factories should be short-running and must not synchronously wait for another
    thread that needs this container. Async factories and awaitable results are
    unsupported. The container does not manage service lifecycle or disposal.
    """

    def __init__(self) -> None:
        """Initialize an empty, isolated container."""
        self._instances: dict[type[object], object] = {}
        self._factories: dict[type[object], _FactoryRegistration[object]] = {}
        self._lock = RLock()
        self._resolution_local = local()

    def register_instance[ServiceT](
        self,
        service_type: type[ServiceT],
        instance: ServiceT,
    ) -> None:
        """Register an existing non-None instance without changing its identity."""
        self._validate_service_type(service_type)
        if instance is None:
            raise TypeError("service instance cannot be None")

        key = cast(type[object], service_type)
        with self._lock:
            self._ensure_unregistered(key)
            self._instances[key] = instance

    def register_factory[ServiceT](
        self,
        service_type: type[ServiceT],
        factory: Callable[[ServiceContainer], ServiceT],
        *,
        lifetime: ServiceLifetime = "singleton",
    ) -> None:
        """Register a synchronous factory with singleton or transient lifetime."""
        self._validate_service_type(service_type)
        if not callable(factory):
            raise TypeError("factory must be callable")
        if lifetime not in ("singleton", "transient"):
            raise ValueError("lifetime must be 'singleton' or 'transient'")

        key = cast(type[object], service_type)
        registration = _FactoryRegistration[object](cast(ServiceFactory[object], factory), lifetime)
        with self._lock:
            self._ensure_unregistered(key)
            self._factories[key] = registration

    def resolve[ServiceT](self, service_type: type[ServiceT]) -> ServiceT:
        """Return a registered instance or construct a service from its factory."""
        self._validate_service_type(service_type)
        key = cast(type[object], service_type)

        with self._lock:
            if key in self._instances:
                return cast(ServiceT, self._instances[key])

            registration = self._factories.get(key)
            if registration is None:
                raise ServiceError(f"service {self._type_name(key)} is not registered")

            if registration.has_instance:
                return cast(ServiceT, registration.instance)

            stack = self._resolution_stack()
            if key in stack:
                cycle = (*stack[stack.index(key) :], key)
                path = " -> ".join(self._type_name(entry) for entry in cycle)
                raise ServiceError(f"circular service dependency: {path}")

            stack.append(key)
            try:
                instance = registration.factory(self)
                if instance is None:
                    raise ServiceError(f"factory for {self._type_name(key)} returned None")
                if inspect.isawaitable(instance):
                    if inspect.iscoroutine(instance):
                        instance.close()
                    raise ServiceError(
                        f"factory for {self._type_name(key)} returned an awaitable; "
                        "async service construction is unsupported"
                    )
                if registration.lifetime == "singleton":
                    registration.instance = instance
                    registration.has_instance = True
                return cast(ServiceT, instance)
            finally:
                stack.pop()

    def contains(self, service_type: type[object]) -> bool:
        """Return whether a service key has been registered."""
        self._validate_service_type(service_type)
        key = service_type
        with self._lock:
            return key in self._instances or key in self._factories

    def _resolution_stack(self) -> list[type[object]]:
        """Return this thread's active factory-resolution path."""
        stack = getattr(self._resolution_local, "stack", None)
        if stack is None:
            stack = []
            self._resolution_local.stack = stack
        return cast(list[type[object]], stack)

    def _ensure_unregistered(self, service_type: type[object]) -> None:
        """Reject duplicate service keys without replacing existing bindings."""
        if service_type in self._instances or service_type in self._factories:
            raise ServiceError(f"service {self._type_name(service_type)} is already registered")

    @staticmethod
    def _validate_service_type(service_type: object) -> None:
        """Require a class object as the registration or resolution key."""
        if not isinstance(service_type, type):
            raise TypeError("service_type must be a class object")

    @staticmethod
    def _type_name(service_type: type[object]) -> str:
        """Return a stable qualified class name for diagnostics."""
        return f"{service_type.__module__}.{service_type.__qualname__}"
