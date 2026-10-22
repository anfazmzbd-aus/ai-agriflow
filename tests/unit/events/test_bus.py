from __future__ import annotations

from agentos.events import Event, EventBus


async def test_event_bus_publishes_to_exact_handlers() -> None:
    """Event bus should deliver events to matching subscribers."""
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe("crop.created", handler)
    event = Event(type="crop.created", payload={"crop": "rice"})

    await bus.publish(event)

    assert received == [event]
    assert bus.subscriber_count("crop.created") == 1


async def test_event_bus_publishes_to_wildcard_handlers() -> None:
    """Event bus should deliver every event to wildcard subscribers."""
    bus = EventBus()
    received: list[str] = []

    async def handler(event: Event) -> None:
        received.append(event.type)

    bus.subscribe("*", handler)

    await bus.publish(Event(type="workflow.completed"))

    assert received == ["workflow.completed"]
