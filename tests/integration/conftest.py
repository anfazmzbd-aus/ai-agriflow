"""Reusable in-memory application fixtures for integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import pytest

from agentos.agents import AgentContext, AgentResult, BaseAgent
from agentos.base import LifecycleComponent
from agentos.core.config import AgentOSSettings
from agentos.events import Event, EventBus
from agentos.runtime import Runtime

Hook = Callable[[], Awaitable[None]]


class AdviceService:
    """Small deterministic service used in place of a real model or API."""

    def advise(self, goal: str) -> str:
        """Return a predictable response for the supplied goal."""
        return f"advice:{goal}"


class TraceComponent(LifecycleComponent):
    """Lifecycle component that records hook order and supports controlled failures."""

    def __init__(self, name: str, trace: list[str]) -> None:
        """Create a component that appends lifecycle calls to a shared trace."""
        super().__init__(name)
        self.trace = trace
        self.initialize_hook: Hook | None = None
        self.start_hook: Hook | None = None
        self.stop_hook: Hook | None = None

    async def _initialize(self) -> None:
        """Record and optionally run the initialization hook."""
        self.trace.append(f"initialize:{self.name}")
        if self.initialize_hook is not None:
            await self.initialize_hook()

    async def _start(self) -> None:
        """Record and optionally run the startup hook."""
        self.trace.append(f"start:{self.name}")
        if self.start_hook is not None:
            await self.start_hook()

    async def _stop(self) -> None:
        """Record and optionally run the cleanup hook."""
        self.trace.append(f"stop:{self.name}")
        if self.stop_hook is not None:
            await self.stop_hook()


class AdviceAgent(BaseAgent[AgentContext, AgentResult]):
    """Typed fake agent that uses explicit service and EventBus references."""

    def __init__(
        self,
        name: str,
        service: AdviceService,
        event_bus: EventBus,
        trace: list[str],
    ) -> None:
        """Store explicitly injected dependencies and lifecycle controls."""
        super().__init__(name)
        self.service = service
        self.event_bus = event_bus
        self.trace = trace
        self.initialize_hook: Hook | None = None
        self.start_hook: Hook | None = None
        self.stop_hook: Hook | None = None
        self.execution_entered: asyncio.Event | None = None
        self.execution_release: asyncio.Event | None = None

    async def _initialize(self) -> None:
        """Record and optionally run the initialization hook."""
        self.trace.append(f"initialize:{self.name}")
        if self.initialize_hook is not None:
            await self.initialize_hook()

    async def _start(self) -> None:
        """Record and optionally run the startup hook."""
        self.trace.append(f"start:{self.name}")
        if self.start_hook is not None:
            await self.start_hook()

    async def _stop(self) -> None:
        """Record and optionally run the cleanup hook."""
        self.trace.append(f"stop:{self.name}")
        if self.stop_hook is not None:
            await self.stop_hook()

    async def _execute(self, agent_input: AgentContext) -> AgentResult:
        """Use the fake service and publish its result as a domain event."""
        if self.execution_entered is not None:
            self.execution_entered.set()
        if self.execution_release is not None:
            await self.execution_release.wait()
        advice = self.service.advise(agent_input.goal)
        await self.event_bus.publish(
            Event(
                type="advice.ready",
                payload={"goal": agent_input.goal, "advice": advice},
            )
        )
        return AgentResult(content=advice, metadata={"service": "fake"})


@dataclass
class TestApplication:
    """A fresh application composition assembled only from public APIs."""

    __test__ = False

    runtime: Runtime
    service: AdviceService
    service_component: TraceComponent
    agent: AdviceAgent
    trace: list[str]
    domain_events: list[Event]


@pytest.fixture
def app_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[], TestApplication]:
    """Return a factory for isolated, unstarted in-memory applications."""
    import agentos.runtime.runtime as runtime_module

    monkeypatch.setattr(runtime_module, "configure_logging", lambda _: None)

    def create() -> TestApplication:
        runtime = Runtime.from_settings(
            AgentOSSettings(environment="integration-test", log_level="WARNING")
        )
        service = AdviceService()
        runtime.services.register_instance(AdviceService, service)
        trace: list[str] = []
        service_component = TraceComponent("service", trace)
        agent = AdviceAgent(
            "advisor",
            runtime.services.resolve(AdviceService),
            runtime.event_bus,
            trace,
        )
        domain_events: list[Event] = []

        async def record_event(event: Event) -> None:
            domain_events.append(event)

        runtime.event_bus.subscribe("advice.ready", record_event)
        runtime.registry.register("advisor", agent)
        # Forward references are supported and make the named dependency explicit.
        runtime.register_component(agent, depends_on=("service",))
        runtime.register_component(service_component)
        return TestApplication(
            runtime=runtime,
            service=service,
            service_component=service_component,
            agent=agent,
            trace=trace,
            domain_events=domain_events,
        )

    return create


@pytest.fixture
def application(app_factory: Callable[[], TestApplication]) -> TestApplication:
    """Provide a fresh composed application without starting it."""
    return app_factory()


async def wait_for(event: asyncio.Event) -> None:
    """Wait for a synchronization event with a bounded hang guard."""
    await asyncio.wait_for(event.wait(), timeout=3)
