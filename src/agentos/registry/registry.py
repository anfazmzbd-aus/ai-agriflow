from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from agentos.base.exceptions import RegistrationError

Registered = TypeVar("Registered")


class Registry[Registered]:
    """Name-addressable registry for framework plugins and components."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._items: dict[str, Registered] = {}

    def register(self, name: str, item: Registered, *, replace: bool = False) -> None:
        """Register an item by name.

        Raises:
            RegistrationError: If the name already exists and replacement is disabled.

        """
        if name in self._items and not replace:
            msg = f"'{name}' is already registered"
            raise RegistrationError(msg)
        self._items[name] = item

    def get(self, name: str) -> Registered:
        """Return a registered item by name.

        Raises:
            RegistrationError: If the name does not exist.

        """
        try:
            return self._items[name]
        except KeyError as exc:
            msg = f"'{name}' is not registered"
            raise RegistrationError(msg) from exc

    def names(self) -> Iterable[str]:
        """Return registered names in insertion order."""
        return self._items.keys()
