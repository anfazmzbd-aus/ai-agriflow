from __future__ import annotations

from agentos.base import Component


class NamedComponent(Component):
    """Concrete component used to verify the base contract."""

    @property
    def name(self) -> str:
        """Return the component name."""
        return "named-component"


def test_component_contract_exposes_name() -> None:
    """Component implementations should expose a stable name."""
    component = NamedComponent()

    assert component.name == "named-component"
