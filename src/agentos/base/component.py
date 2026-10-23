from __future__ import annotations

from abc import ABC, abstractmethod


class Component(ABC):
    """Base contract for AgentOS framework components."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable component name."""


class BaseComponent(Component):
    """Reusable component base that stores a validated, stable name."""

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        """Initialize the component with a non-empty name.

        The supplied name is preserved exactly; validation only rejects values
        that are not strings or contain no non-whitespace characters.
        """
        if not isinstance(name, str):
            raise ValueError("component name must be a string")
        if not name.strip():
            raise ValueError("component name must contain a non-whitespace character")
        self._name = name

    @property
    def name(self) -> str:
        """Return the component's stable name."""
        return self._name
