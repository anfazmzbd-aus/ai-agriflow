"""Asynchronous lifecycle coordination for explicitly registered components."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from agentos.base.exceptions import AgentOSRuntimeError, ConfigurationError, RegistrationError
from agentos.base.lifecycle import LifecycleComponent, LifecycleState
from agentos.registry import Registry


class ComponentManager:
    """Manage lifecycle order and cleanup for named lifecycle components.

    Dependencies refer to other component names. Components are initialized and
    started in stable topological order, then stopped in reverse order. The manager
    coordinates lifecycle only; it does not construct components or drain agent work.
    """

    def __init__(self) -> None:
        """Create an empty manager in the NEW state."""
        self._registry: Registry[LifecycleComponent] = Registry()
        self._dependencies: dict[str, tuple[str, ...]] = {}
        self._registration_order: list[str] = []
        self._component_ids: set[int] = set()
        self._state = LifecycleState.NEW
        self._lock = asyncio.Lock()
        self._owner: asyncio.Task[object] | None = None
        self._operation_active = False
        self._registration_closed = False
        self._ordered_names: tuple[str, ...] | None = None

    @property
    def state(self) -> LifecycleState:
        """Return the aggregate lifecycle state."""
        return self._state

    def register(
        self,
        component: LifecycleComponent,
        *,
        depends_on: Iterable[str] = (),
    ) -> None:
        """Register a component and its named lifecycle dependencies.

        Forward references are allowed. The complete graph is validated before
        lifecycle hooks run. Registration closes after initialization preflight and
        before the first lifecycle hook begins.
        """
        if self._registration_closed or self._operation_active:
            raise AgentOSRuntimeError("cannot register components after initialization begins")
        if not isinstance(component, LifecycleComponent):
            raise TypeError("component must be a LifecycleComponent")
        if id(component) in self._component_ids:
            raise RegistrationError(f"component object {component.name!r} is already registered")
        dependencies = tuple(depends_on)
        if any(not isinstance(name, str) or not name.strip() for name in dependencies):
            raise ConfigurationError("dependency names must be non-empty strings")
        if len(set(dependencies)) != len(dependencies):
            raise ConfigurationError(
                f"component {component.name!r} declares duplicate dependencies"
            )
        if component.name in dependencies:
            raise ConfigurationError(f"component {component.name!r} cannot depend on itself")
        self._registry.register(component.name, component)
        self._dependencies[component.name] = dependencies
        self._registration_order.append(component.name)
        self._component_ids.add(id(component))

    def get(self, name: str) -> LifecycleComponent:
        """Return a component by name using existing Registry semantics."""
        return self._registry.get(name)

    def names(self) -> tuple[str, ...]:
        """Return registered names in insertion order."""
        return tuple(self._registration_order)

    async def initialize(self) -> None:
        """Initialize all components in dependency order."""
        async with self._operation("initialize"):
            if self._state is LifecycleState.INITIALIZED:
                return
            self._require_state("initialize", LifecycleState.NEW)
            ordered = self._topological_order()
            invalid = [
                f"{name}={self.get(name).lifecycle_state.value}"
                for name in ordered
                if self.get(name).lifecycle_state is not LifecycleState.NEW
            ]
            if invalid:
                raise ConfigurationError(
                    "all managed components must be NEW before initialization: "
                    + ", ".join(invalid)
                )
            self._registration_closed = True
            self._ordered_names = ordered
            attempted: list[str] = []
            try:
                for name in ordered:
                    attempted.append(name)
                    await self.get(name).initialize()
            except BaseException as primary:
                self._state = LifecycleState.FAILED
                cleanup_errors = await self._cleanup_names(reversed(attempted))
                self._raise_with_cleanup(primary, cleanup_errors, "initialization rollback")
            self._state = LifecycleState.INITIALIZED

    async def start(self) -> None:
        """Start every initialized component in dependency order."""
        async with self._operation("start"):
            if self._state is LifecycleState.STARTED:
                return
            self._require_state("start", LifecycleState.INITIALIZED)
            if self._ordered_names is None:
                raise AgentOSRuntimeError("manager has no validated component order")
            try:
                for name in self._ordered_names:
                    await self.get(name).start()
            except BaseException as primary:
                self._state = LifecycleState.FAILED
                cleanup_errors = await self._cleanup_names(reversed(self._ordered_names))
                self._raise_with_cleanup(primary, cleanup_errors, "startup rollback")
            self._state = LifecycleState.STARTED

    async def stop(self) -> None:
        """Stop components in reverse order, attempting every required cleanup."""
        async with self._operation("stop"):
            if self._state is LifecycleState.STOPPED:
                return
            if self._state is LifecycleState.NEW:
                ordered = tuple(self._registration_order)
            elif self._state in (
                LifecycleState.INITIALIZED,
                LifecycleState.STARTED,
                LifecycleState.FAILED,
            ):
                ordered = self._ordered_names or self._topological_order()
            else:
                raise AgentOSRuntimeError(f"cannot stop manager from {self._state.value}")
            self._registration_closed = True
            errors = await self._cleanup_names(reversed(ordered))
            if errors:
                self._state = LifecycleState.FAILED
                ordinary = [error for error in errors if isinstance(error, Exception)]
                controls = [error for error in errors if not isinstance(error, Exception)]
                if controls:
                    self._raise_with_cleanup(controls[0], [*controls[1:], *ordinary], "shutdown")
                raise ExceptionGroup("component shutdown failed", ordinary)
            self._state = LifecycleState.STOPPED

    async def _cleanup_names(self, names: Iterable[str]) -> list[BaseException]:
        """Stop all non-stopped named components and collect every failure."""
        errors: list[BaseException] = []
        for name in names:
            component = self.get(name)
            if component.lifecycle_state is LifecycleState.STOPPED:
                continue
            try:
                await component.stop()
            except BaseException as exc:
                errors.append(exc)
        return errors

    def _topological_order(self) -> tuple[str, ...]:
        """Validate and produce stable Kahn ordering for the dependency graph."""
        registered = set(self._registration_order)
        for name in self._registration_order:
            missing = [dep for dep in self._dependencies[name] if dep not in registered]
            if missing:
                raise ConfigurationError(
                    f"component {name!r} has missing dependencies: {', '.join(missing)}"
                )
        positions = {name: index for index, name in enumerate(self._registration_order)}
        remaining = {name: set(self._dependencies[name]) for name in self._registration_order}
        ordered: list[str] = []
        while remaining:
            eligible = [name for name, deps in remaining.items() if not deps]
            if not eligible:
                cycle = self._find_cycle(remaining)
                raise ConfigurationError(f"component dependency cycle: {' -> '.join(cycle)}")
            name = min(eligible, key=positions.__getitem__)
            ordered.append(name)
            del remaining[name]
            for dependencies in remaining.values():
                dependencies.discard(name)
        return tuple(ordered)

    def _find_cycle(self, remaining: dict[str, set[str]]) -> list[str]:
        """Return a readable dependency cycle from the unresolved graph."""
        visiting: list[str] = []
        active: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> list[str] | None:
            if name in active:
                return [*visiting[visiting.index(name) :], name]
            if name in visited:
                return None
            active.add(name)
            visiting.append(name)
            for dependency in sorted(remaining[name]):
                result = visit(dependency)
                if result is not None:
                    return result
            visiting.pop()
            active.remove(name)
            visited.add(name)
            return None

        for name in self._registration_order:
            if name in remaining:
                cycle = visit(name)
                if cycle is not None:
                    return cycle
        return []

    def _require_state(self, operation: str, expected: LifecycleState) -> None:
        """Reject an aggregate transition that is not allowed."""
        if self._state is not expected:
            raise AgentOSRuntimeError(
                f"cannot {operation} manager from {self._state.value}; expected {expected.value}"
            )

    def _operation(self, operation: str) -> _ManagerOperation:
        """Create a serialized operation context with recursive-call protection."""
        current = asyncio.current_task()
        if current is not None and current is self._owner:
            raise AgentOSRuntimeError(f"manager {operation} cannot be called recursively")
        return _ManagerOperation(self)

    def _raise_with_cleanup(
        self,
        primary: BaseException,
        cleanup_errors: list[BaseException],
        context: str,
    ) -> None:
        """Preserve process-control exceptions and aggregate ordinary failures."""
        if not cleanup_errors:
            raise primary.with_traceback(primary.__traceback__)
        if isinstance(primary, Exception):
            ordinary = [error for error in cleanup_errors if isinstance(error, Exception)]
            controls = [error for error in cleanup_errors if not isinstance(error, Exception)]
            if controls:
                controls[0].add_note(
                    f"{context} followed {type(primary).__name__} and also encountered "
                    f"{len(ordinary)} ordinary cleanup failure(s)"
                )
                raise controls[0].with_traceback(controls[0].__traceback__) from primary
            raise ExceptionGroup(context, [primary, *ordinary])
        for cleanup_error in cleanup_errors:
            primary.add_note(f"{context} cleanup also raised {type(cleanup_error).__name__}")
        raise primary.with_traceback(primary.__traceback__)


class _ManagerOperation:
    """Async context for lifecycle serialization and owner tracking."""

    def __init__(self, manager: ComponentManager) -> None:
        self.manager = manager

    async def __aenter__(self) -> None:
        await self.manager._lock.acquire()
        self.manager._owner = asyncio.current_task()
        self.manager._operation_active = True

    async def __aexit__(self, *_: object) -> None:
        self.manager._operation_active = False
        self.manager._owner = None
        self.manager._lock.release()
