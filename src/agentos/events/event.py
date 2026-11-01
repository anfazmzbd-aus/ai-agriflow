from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from agentos.utils.clock import utc_now
from agentos.utils.ids import new_id


class Event(BaseModel):
    """Mutable in-process event with a Python mapping payload."""

    id: str = Field(default_factory=new_id)
    type: str
    payload: Mapping[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        """Require a nonblank event type while preserving its supplied value."""
        if not value.strip():
            raise ValueError("event type must contain a non-whitespace character")
        return value
