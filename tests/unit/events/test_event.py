from __future__ import annotations

from typing import cast

import pytest
from pydantic import ValidationError

from agentos.events import Event


@pytest.mark.parametrize("event_type", ["", " \t\n"])
def test_event_rejects_blank_type(event_type: str) -> None:
    """Event types must contain at least one non-whitespace character."""
    with pytest.raises(ValidationError, match="non-whitespace"):
        Event(type=event_type)


def test_event_preserves_valid_type_exactly() -> None:
    """Validation does not normalize a valid event type."""
    event = Event(type="  crop.created  ")

    assert event.type == "  crop.created  "


def test_event_constructor_retains_existing_fields_and_mutability() -> None:
    """Existing fields remain available and the event/payload stay mutable."""
    event = Event(type="crop.created", payload={"items": []})
    original_created_at = event.created_at
    original_id = event.id
    payload = cast(dict[str, object], event.payload)

    event.type = "crop.updated"
    payload["extra"] = "value"
    cast(list[object], payload["items"]).append("rice")

    assert event.type == "crop.updated"
    assert event.id == original_id
    assert event.created_at == original_created_at
    assert payload["extra"] == "value"
    assert payload["items"] == ["rice"]


def test_event_rejects_non_string_type() -> None:
    """Pydantic's existing string validation remains in force."""
    with pytest.raises(ValidationError):
        Event(type=cast(str, 42))
