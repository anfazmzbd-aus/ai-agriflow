from __future__ import annotations

from abc import ABC, abstractmethod


class Component(ABC):
    """Base contract for AgentOS framework components."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable component name."""
