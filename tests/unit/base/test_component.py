from __future__ import annotations

import pytest

from agentos.base import BaseComponent, Component


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


@pytest.mark.parametrize("name", ["worker", " Worker ", "\t worker\n"])
def test_base_component_accepts_and_preserves_valid_names(name: str) -> None:
    """BaseComponent accepts names containing non-whitespace and preserves them."""
    component = BaseComponent(name)

    assert component.name == name
    assert isinstance(component, Component)


@pytest.mark.parametrize("name", ["", " ", "\t\n"])
def test_base_component_rejects_empty_or_whitespace_names(name: str) -> None:
    """BaseComponent rejects names without a non-whitespace character."""
    with pytest.raises(ValueError, match="non-whitespace"):
        BaseComponent(name)


@pytest.mark.parametrize("name", [None, 1, object()])
def test_base_component_rejects_non_string_names(name: object) -> None:
    """BaseComponent rejects values that are not strings."""
    with pytest.raises(ValueError, match="must be a string"):
        BaseComponent(name)  # type: ignore[arg-type]


def test_base_component_is_concrete_and_name_is_read_only() -> None:
    """BaseComponent can be instantiated directly and exposes no name setter."""
    component = BaseComponent("concrete")

    assert component.name == "concrete"
    with pytest.raises(AttributeError):
        component.name = "changed"  # type: ignore[misc]


def test_base_component_does_not_add_lifecycle_api() -> None:
    """Lifecycle operations remain outside the component identity contract."""
    assert not hasattr(BaseComponent, "initialize")
    assert not hasattr(BaseComponent, "start")
    assert not hasattr(BaseComponent, "stop")
