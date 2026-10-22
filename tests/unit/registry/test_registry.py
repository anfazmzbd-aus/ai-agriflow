from __future__ import annotations

import pytest

from agentos.base import RegistrationError
from agentos.registry import Registry


def test_registry_registers_and_reads_items() -> None:
    """Registry should return registered items by name."""
    registry = Registry[int]()

    registry.register("answer", 42)

    assert registry.get("answer") == 42
    assert list(registry.names()) == ["answer"]


def test_registry_rejects_duplicate_names() -> None:
    """Registry should protect existing names by default."""
    registry = Registry[str]()
    registry.register("tool", "first")

    with pytest.raises(RegistrationError):
        registry.register("tool", "second")


def test_registry_can_replace_items() -> None:
    """Registry should support explicit replacement."""
    registry = Registry[str]()
    registry.register("tool", "first")

    registry.register("tool", "second", replace=True)

    assert registry.get("tool") == "second"


def test_registry_rejects_unknown_names() -> None:
    """Registry should raise for unknown names."""
    registry = Registry[str]()

    with pytest.raises(RegistrationError):
        registry.get("missing")
