from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from pydantic import BaseModel, Field

from agentos.utils.clock import utc_now
from agentos.utils.ids import new_id


class Event(BaseModel):
    """Immutable message published through the AgentOS event bus."""

    id: str = Field(default_factory=new_id)
    type: str
    payload: Mapping[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
