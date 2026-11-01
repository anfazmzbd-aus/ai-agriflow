from __future__ import annotations

import asyncio
from typing import cast

import pytest

from agentos.core.config import AgentOSSettings
from agentos.events import Event, EventBus, EventHandler
from agentos.runtime import Runtime


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


@pytest.mark.asyncio
async def test_exact_handlers_run_before_wildcards_in_registration_order() -> None:
    """Dispatch is sequential: exact registrations, then wildcard registrations."""
    bus = EventBus()
    received: list[str] = []

    async def record(label: str, event: Event) -> None:
        received.append(label)

    async def exact_one(event: Event) -> None:
        await record("exact-1", event)

    async def exact_two(event: Event) -> None:
        await record("exact-2", event)

    async def wildcard_one(event: Event) -> None:
        await record("wildcard-1", event)

    async def wildcard_two(event: Event) -> None:
        await record("wildcard-2", event)

    bus.subscribe("crop.created", exact_one)
    bus.subscribe("*", wildcard_one)
    bus.subscribe("crop.created", exact_two)
    bus.subscribe("*", wildcard_two)

    await bus.publish(Event(type="crop.created"))

    assert received == ["exact-1", "exact-2", "wildcard-1", "wildcard-2"]


@pytest.mark.asyncio
async def test_duplicate_subscriptions_deliver_independently_and_unsubscribe_one() -> None:
    """Each registration is distinct; unsubscribe removes the first equal one."""
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe("crop.created", handler)
    bus.subscribe("crop.created", handler)
    assert bus.subscriber_count("crop.created") == 2

    await bus.publish(Event(type="crop.created"))
    assert len(received) == 2

    assert bus.unsubscribe("crop.created", handler) is True
    assert bus.subscriber_count("crop.created") == 1
    assert bus.unsubscribe("crop.created", handler) is True
    assert bus.subscriber_count("crop.created") == 0
    assert bus.unsubscribe("crop.created", handler) is False


def test_subscribe_and_unsubscribe_validate_arguments() -> None:
    """Event types must be nonblank strings and handlers must be callable."""
    bus = EventBus()

    with pytest.raises(ValueError, match="non-whitespace"):
        bus.subscribe(" \t", cast(EventHandler, lambda event: None))
    with pytest.raises(TypeError, match="event_type"):
        bus.subscribe(cast(str, 5), cast(EventHandler, lambda event: None))
    with pytest.raises(TypeError, match="handler"):
        bus.subscribe("crop.created", cast(EventHandler, None))
    with pytest.raises(TypeError, match="handler"):
        bus.unsubscribe("crop.created", cast(EventHandler, None))
    with pytest.raises(ValueError, match="non-whitespace"):
        bus.unsubscribe("", cast(EventHandler, lambda event: None))
    with pytest.raises(TypeError, match="event_type"):
        bus.unsubscribe(cast(str, 5), cast(EventHandler, lambda event: None))


def test_subscriber_count_is_side_effect_free_and_missing_publish_is_noop() -> None:
    """Unknown types do not create entries and publications with no handlers work."""
    bus = EventBus()

    assert bus.subscriber_count("unregistered") == 0
    assert bus._handlers == {}

    asyncio.run(bus.publish(Event(type="unregistered")))

    assert bus._handlers == {}


@pytest.mark.asyncio
async def test_wildcard_event_type_does_not_double_deliver_global_registrations() -> None:
    """Publishing type '*' selects each wildcard registration once."""
    bus = EventBus()
    received: list[str] = []

    async def handler(event: Event) -> None:
        received.append(event.type)

    bus.subscribe("*", handler)
    bus.subscribe("*", handler)
    assert bus.subscriber_count("*") == 2

    await bus.publish(Event(type="*"))

    assert received == ["*", "*"]


@pytest.mark.asyncio
async def test_unsubscribe_uses_handler_equality_for_bound_methods() -> None:
    """A freshly accessed bound method can remove the matching registration."""
    bus = EventBus()
    received: list[Event] = []

    class Listener:
        async def handle(self, event: Event) -> None:
            received.append(event)

    listener = Listener()
    bus.subscribe("bound.method", listener.handle)

    assert bus.unsubscribe("bound.method", listener.handle) is True
    await bus.publish(Event(type="bound.method"))
    assert received == []


@pytest.mark.asyncio
async def test_other_star_strings_are_literal_event_types() -> None:
    """Only the exact subscription type '*' is the global wildcard."""
    bus = EventBus()
    received: list[str] = []

    async def handler(event: Event) -> None:
        received.append(event.type)

    bus.subscribe("crop.*", handler)

    await bus.publish(Event(type="crop.created"))
    await bus.publish(Event(type="crop.*"))

    assert received == ["crop.*"]


@pytest.mark.asyncio
async def test_subscription_during_publish_affects_only_later_publications() -> None:
    """The current dispatch uses a snapshot taken before callbacks run."""
    bus = EventBus()
    received: list[str] = []
    subscribed = False

    async def late_handler(event: Event) -> None:
        received.append("late")

    async def subscribing_handler(event: Event) -> None:
        nonlocal subscribed
        received.append("first")
        if not subscribed:
            subscribed = True
            bus.subscribe(event.type, late_handler)

    bus.subscribe("snapshot.test", subscribing_handler)

    await bus.publish(Event(type="snapshot.test"))
    assert received == ["first"]

    await bus.publish(Event(type="snapshot.test"))
    assert received == ["first", "first", "late"]


@pytest.mark.asyncio
async def test_unsubscription_during_publish_affects_only_later_publications() -> None:
    """Removing a handler does not alter the in-progress snapshot."""
    bus = EventBus()
    received: list[str] = []

    async def removed_handler(event: Event) -> None:
        received.append("removed")

    async def removing_handler(event: Event) -> None:
        received.append("remover")
        bus.unsubscribe(event.type, removed_handler)

    bus.subscribe("snapshot.test", removing_handler)
    bus.subscribe("snapshot.test", removed_handler)

    await bus.publish(Event(type="snapshot.test"))
    assert received == ["remover", "removed"]

    await bus.publish(Event(type="snapshot.test"))
    assert received == ["remover", "removed", "remover"]


@pytest.mark.asyncio
async def test_handler_failure_propagates_unchanged_and_stops_dispatch() -> None:
    """The first handler exception retains identity/traceback and skips later ones."""
    bus = EventBus()
    expected = RuntimeError("subscriber failed")
    called: list[str] = []

    async def failing_handler(event: Event) -> None:
        called.append("failing")
        raise expected

    async def later_handler(event: Event) -> None:
        called.append("later")

    bus.subscribe("failure.test", failing_handler)
    bus.subscribe("failure.test", later_handler)

    with pytest.raises(RuntimeError) as captured:
        await bus.publish(Event(type="failure.test"))

    assert captured.value is expected
    assert called == ["failing"]
    traceback = captured.value.__traceback__
    frame_names: list[str] = []
    while traceback is not None:
        frame_names.append(traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    assert "failing_handler" in frame_names


@pytest.mark.asyncio
async def test_cancellation_propagates_and_skips_later_handlers() -> None:
    """Cancelling a blocked subscriber stops this publication unchanged."""
    bus = EventBus()
    entered = asyncio.Event()
    release = asyncio.Event()
    later_called = False

    async def blocking_handler(event: Event) -> None:
        entered.set()
        await release.wait()

    async def later_handler(event: Event) -> None:
        nonlocal later_called
        later_called = True

    bus.subscribe("cancel.test", blocking_handler)
    bus.subscribe("cancel.test", later_handler)
    task = asyncio.create_task(bus.publish(Event(type="cancel.test")))
    await asyncio.wait_for(entered.wait(), timeout=2)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert later_called is False


@pytest.mark.asyncio
async def test_concurrent_publications_can_interleave() -> None:
    """Publications have independent snapshots and are not globally serialized."""
    bus = EventBus()
    entered_count = 0
    both_entered = asyncio.Event()
    release = asyncio.Event()

    async def blocking_handler(event: Event) -> None:
        nonlocal entered_count
        entered_count += 1
        if entered_count == 2:
            both_entered.set()
        await release.wait()

    bus.subscribe("concurrent.test", blocking_handler)
    first = asyncio.create_task(bus.publish(Event(type="concurrent.test")))
    second = asyncio.create_task(bus.publish(Event(type="concurrent.test")))
    await asyncio.wait_for(both_entered.wait(), timeout=2)
    release.set()
    await asyncio.gather(first, second)

    assert entered_count == 2


@pytest.mark.asyncio
async def test_runtime_still_constructs_compatible_event_bus() -> None:
    """The Runtime's public EventBus field remains constructible and usable."""
    runtime = Runtime.from_settings(AgentOSSettings(environment="test"))
    assert isinstance(runtime.event_bus, EventBus)

    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    runtime.event_bus.subscribe("runtime.test", handler)
    await runtime.event_bus.publish(Event(type="runtime.test"))
    assert len(received) == 1
