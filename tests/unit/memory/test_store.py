from __future__ import annotations

from agentos.memory import InMemoryStore


def test_in_memory_store_puts_and_gets_records() -> None:
    """InMemoryStore should retain records by key."""
    store = InMemoryStore()

    record = store.put("field:1", {"crop": "rice"}, {"region": "south"})

    assert store.get("field:1") == record
    assert list(store.list()) == [record]
    assert record.metadata["region"] == "south"
