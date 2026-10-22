from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

from agentos.utils.clock import utc_now


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    """Structured telemetry event emitted by framework components."""

    name: str
    attributes: Mapping[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


class InMemoryTelemetrySink:
    """In-memory telemetry sink for local development and tests."""

    def __init__(self) -> None:
        """Initialize an empty telemetry sink."""
        self._events: list[TelemetryEvent] = []

    def emit(self, event: TelemetryEvent) -> None:
        """Record a telemetry event."""
        self._events.append(event)

    def list(self) -> Iterable[TelemetryEvent]:
        """Return telemetry events in emission order."""
        return tuple(self._events)
