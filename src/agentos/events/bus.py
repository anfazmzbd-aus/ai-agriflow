from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable

from agentos.events.event import Event

EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """In-process asynchronous publish/subscribe event bus."""

    def __init__(self) -> None:
        """Initialize an empty event bus."""
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register an asynchronous handler for an event type."""
        self._handlers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        """Publish an event to exact-match and wildcard subscribers."""
        handlers = [*self._handlers[event.type], *self._handlers["*"]]
        for handler in handlers:
            await handler(event)

    def subscriber_count(self, event_type: str) -> int:
        """Return the number of handlers registered for an event type."""
        return len(self._handlers[event_type])
