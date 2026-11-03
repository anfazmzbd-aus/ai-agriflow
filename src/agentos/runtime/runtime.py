from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import cast

from agentos.base.exceptions import AgentOSRuntimeError, ServiceError
from agentos.base.lifecycle import LifecycleComponent, LifecycleState
from agentos.container import ServiceContainer
from agentos.core.config import AgentOSSettings
from agentos.core.logging import configure_logging
from agentos.events import EventBus
from agentos.manager import ComponentManager
from agentos.registry import Registry
from agentos.telemetry import InMemoryTelemetrySink, TelemetryEvent


@dataclass(slots=True)
class Runtime:
    """Coordinates framework startup concerns for an AgentOS application."""

    settings: AgentOSSettings
    event_bus: EventBus
    registry: Registry[object]
    telemetry: InMemoryTelemetrySink
    services: ServiceContainer = field(default_factory=ServiceContainer, repr=False, compare=False)
    component_manager: ComponentManager = field(
        default_factory=ComponentManager, repr=False, compare=False
    )
    _lifecycle_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _lifecycle_owner: asyncio.Task[object] | None = field(default=None, init=False, repr=False)
    _managed_lifecycle_requested: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        """Bind core Runtime objects without replacing existing registrations."""
        self._register_core_services()

    @property
    def state(self) -> LifecycleState:
        """Return the state owned by the Runtime's ComponentManager."""
        return self.component_manager.state

    def register_component(
        self,
        component: LifecycleComponent,
        *,
        depends_on: Iterable[str] = (),
    ) -> None:
        """Register one lifecycle component with the manager."""
        self.component_manager.register(component, depends_on=depends_on)

    def start(self) -> None:
        """Run the legacy synchronous logging and telemetry startup operation.

        This does not initialize or start managed components. Calls are rejected
        once a managed lifecycle operation has been requested.
        """
        if self._managed_lifecycle_requested or self._lifecycle_lock.locked():
            raise AgentOSRuntimeError(
                "legacy Runtime.start() is unavailable after managed lifecycle begins"
            )
        configure_logging(self.settings.log_level)
        self.telemetry.emit(
            TelemetryEvent(
                name="runtime.started",
                attributes={"environment": self.settings.environment},
            )
        )

    async def initialize_async(self) -> None:
        """Configure logging, initialize components, then report the transition."""
        self._managed_lifecycle_requested = True
        async with self._operation("initialize"):
            previous = self.state
            try:
                configure_logging(self.settings.log_level)
                await self.component_manager.initialize()
            except (Exception, asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                if self.state is LifecycleState.FAILED:
                    self._emit_lifecycle_failure("initialize")
                raise
            if (
                previous is not LifecycleState.INITIALIZED
                and self.state is LifecycleState.INITIALIZED
            ):
                self._emit_lifecycle_event("runtime.initialized")

    async def start_async(self) -> None:
        """Start initialized components and report successful managed readiness."""
        self._managed_lifecycle_requested = True
        async with self._operation("start"):
            previous = self.state
            try:
                await self.component_manager.start()
            except (Exception, asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                if self.state is LifecycleState.FAILED:
                    self._emit_lifecycle_failure("start")
                raise
            if previous is not LifecycleState.STARTED and self.state is LifecycleState.STARTED:
                self._emit_lifecycle_event("runtime.started")

    async def stop_async(self) -> None:
        """Stop managed components and report successful shutdown."""
        self._managed_lifecycle_requested = True
        async with self._operation("stop"):
            previous = self.state
            try:
                await self.component_manager.stop()
            except (Exception, asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                if self.state is LifecycleState.FAILED:
                    self._emit_lifecycle_failure("stop")
                raise
            if previous is not LifecycleState.STOPPED and self.state is LifecycleState.STOPPED:
                self._emit_lifecycle_event("runtime.stopped")

    @classmethod
    def from_settings(cls, settings: AgentOSSettings | None = None) -> Runtime:
        """Create a runtime from explicit settings or environment configuration."""
        return cls(
            settings=settings or AgentOSSettings(),
            event_bus=EventBus(),
            registry=Registry(),
            telemetry=InMemoryTelemetrySink(),
        )

    def _register_core_services(self) -> None:
        """Preflight all core type keys before adding any missing binding."""
        core: tuple[tuple[type[object], object], ...] = (
            (AgentOSSettings, self.settings),
            (EventBus, self.event_bus),
            (Registry, self.registry),
            (InMemoryTelemetrySink, self.telemetry),
            (ServiceContainer, self.services),
            (ComponentManager, self.component_manager),
        )
        conflicts = [
            f"{service_type.__name__} is already registered"
            for service_type, _ in core
            if self.services.contains(service_type)
        ]
        if conflicts:
            raise ServiceError("Runtime core service collision: " + "; ".join(conflicts))
        for service_type, instance in core:
            self._register_core_service(service_type, instance)

    def _register_core_service[ServiceT](
        self, service_type: type[ServiceT], instance: object
    ) -> None:
        """Register one known core service after the complete collision preflight."""
        self.services.register_instance(service_type, cast(ServiceT, instance))

    def _emit_lifecycle_event(self, name: str, *, operation: str | None = None) -> None:
        """Emit best-effort managed telemetry after a successful state transition."""
        try:
            attributes: dict[str, object] = {"environment": self.settings.environment}
            if operation is not None:
                attributes["operation"] = operation
            self.telemetry.emit(
                TelemetryEvent(
                    name=name,
                    attributes=attributes,
                )
            )
        except Exception:
            # Diagnostics do not change managed lifecycle outcomes.
            return

    def _emit_lifecycle_failure(self, operation: str) -> None:
        """Attempt failure telemetry without replacing ordinary lifecycle errors."""
        self._emit_lifecycle_event("runtime.lifecycle_failed", operation=operation)

    def _operation(self, operation: str) -> _RuntimeOperation:
        """Create the serialized lifecycle context with recursive-call protection."""
        current = asyncio.current_task()
        if current is not None and current is self._lifecycle_owner:
            raise AgentOSRuntimeError(f"Runtime {operation} cannot be called recursively")
        return _RuntimeOperation(self)


class _RuntimeOperation:
    """Private async lock context for Runtime lifecycle calls."""

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    async def __aenter__(self) -> None:
        await self.runtime._lifecycle_lock.acquire()
        self.runtime._lifecycle_owner = asyncio.current_task()

    async def __aexit__(self, *_: object) -> None:
        self.runtime._lifecycle_owner = None
        self.runtime._lifecycle_lock.release()
