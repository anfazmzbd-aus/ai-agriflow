from __future__ import annotations

from agentos.telemetry import InMemoryTelemetrySink, TelemetryEvent


def test_in_memory_telemetry_records_events() -> None:
    """Telemetry sink should retain emitted events."""
    sink = InMemoryTelemetrySink()
    event = TelemetryEvent(name="runtime.started")

    sink.emit(event)

    assert list(sink.list()) == [event]
