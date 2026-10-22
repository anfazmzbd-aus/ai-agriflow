from __future__ import annotations

from uuid import uuid4


def new_id() -> str:
    """Return a random stable string identifier."""
    return uuid4().hex
