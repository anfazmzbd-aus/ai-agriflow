from __future__ import annotations

from collections.abc import Awaitable, Callable

from agentos.events.event import Event

EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """In-process asynchronous publish/subscribe event bus."""

    def __init__(self) -> None:
        """Initialize an empty event bus."""
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register an asynchronous handler for an event type."""
        self._validate_event_type(event_type)
        self._validate_handler(handler)
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """Remove the first equal handler registration, if one exists.

        Duplicate registrations are independent; each call removes at most one.
        """
        self._validate_event_type(event_type)
        self._validate_handler(handler)
        handlers = self._handlers.get(event_type)
        if handlers is None:
            return False

        try:
            handlers.remove(handler)
        except ValueError:
            return False

        if not handlers:
            del self._handlers[event_type]
        return True

    async def publish(self, event: Event) -> None:
        """Dispatch to a snapshot of exact handlers, then global wildcards.

        Handlers run sequentially for this publication. Registrations changed by
        a handler affect later publishes, not the current snapshot. Concurrent
        publications are independent and may interleave.
        """
        exact_handlers = tuple(self._handlers.get(event.type, ()))
        if event.type == "*":
            handlers = exact_handlers
        else:
            wildcard_handlers = tuple(self._handlers.get("*", ()))
            handlers = (*exact_handlers, *wildcard_handlers)

        for handler in handlers:
            await handler(event)

    def subscriber_count(self, event_type: str) -> int:
        """Return exact registrations; for ``"*"``, return global registrations."""
        self._validate_event_type(event_type)
        return len(self._handlers.get(event_type, ()))

    @staticmethod
    def _validate_event_type(event_type: str) -> None:
        """Reject non-string and blank subscription types without normalization."""
        if not isinstance(event_type, str):
            raise TypeError("event_type must be a string")
        if not event_type.strip():
            raise ValueError("event_type must contain a non-whitespace character")

    @staticmethod
    def _validate_handler(handler: EventHandler) -> None:
        """Reject values that cannot be invoked as event handlers."""
        if not callable(handler):
            raise TypeError("handler must be callable")
