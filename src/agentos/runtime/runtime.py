from __future__ import annotations

from dataclasses import dataclass

from agentos.core.config import AgentOSSettings
from agentos.core.logging import configure_logging
from agentos.events import EventBus
from agentos.registry import Registry
from agentos.telemetry import InMemoryTelemetrySink, TelemetryEvent


@dataclass(slots=True)
class Runtime:
    """Coordinates framework startup concerns for an AgentOS application."""

    settings: AgentOSSettings
    event_bus: EventBus
    registry: Registry[object]
    telemetry: InMemoryTelemetrySink

    def start(self) -> None:
        """Start the runtime services required by the application."""
        configure_logging(self.settings.log_level)
        self.telemetry.emit(
            TelemetryEvent(
                name="runtime.started",
                attributes={"environment": self.settings.environment},
            )
        )

    @classmethod
    def from_settings(cls, settings: AgentOSSettings | None = None) -> Runtime:
        """Create a runtime from explicit settings or environment configuration."""
        return cls(
            settings=settings or AgentOSSettings(),
            event_bus=EventBus(),
            registry=Registry(),
            telemetry=InMemoryTelemetrySink(),
        )
