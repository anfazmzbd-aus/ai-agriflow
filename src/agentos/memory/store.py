from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

from agentos.utils.clock import utc_now
from agentos.utils.ids import new_id


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    """Single memory item stored by an AgentOS memory backend."""

    key: str
    value: object
    id: str = field(default_factory=new_id)
    metadata: Mapping[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


class InMemoryStore:
    """Simple in-process memory store for tests and local workflows."""

    def __init__(self) -> None:
        """Initialize an empty memory store."""
        self._records: dict[str, MemoryRecord] = {}

    def put(
        self,
        key: str,
        value: object,
        metadata: Mapping[str, object] | None = None,
    ) -> MemoryRecord:
        """Store a memory record by key and return the stored record."""
        record = MemoryRecord(key=key, value=value, metadata=metadata or {})
        self._records[key] = record
        return record

    def get(self, key: str) -> MemoryRecord | None:
        """Return a memory record by key when present."""
        return self._records.get(key)

    def list(self) -> Iterable[MemoryRecord]:
        """Return memory records in insertion order."""
        return self._records.values()
