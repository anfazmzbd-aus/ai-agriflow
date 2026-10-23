"""Tests for the public AgentOS exception hierarchy."""

from __future__ import annotations

import pytest

from agentos.base import (
    AgentError,
    AgentOSError,
    AgentOSMemoryError,
    AgentOSRuntimeError,
    ComponentError,
    ConfigurationError,
    ModelError,
    RegistrationError,
    RegistryError,
    ToolError,
    WorkflowError,
)


def test_domain_exceptions_share_agentos_root() -> None:
    """Each domain exception can be caught through the AgentOS root."""
    exception_types = (
        AgentOSRuntimeError,
        WorkflowError,
        AgentError,
        ToolError,
        ModelError,
        AgentOSMemoryError,
        ConfigurationError,
        RegistryError,
    )

    assert all(issubclass(exception_type, AgentOSError) for exception_type in exception_types)


def test_component_errors_share_component_base() -> None:
    """Operational domain failures derive from the component error base."""
    component_types = (
        AgentOSRuntimeError,
        WorkflowError,
        AgentError,
        ToolError,
        ModelError,
        AgentOSMemoryError,
        RegistryError,
    )

    assert all(issubclass(exception_type, ComponentError) for exception_type in component_types)
    assert issubclass(ConfigurationError, AgentOSError)
    assert not issubclass(ConfigurationError, ComponentError)


def test_registration_error_remains_compatible() -> None:
    """Existing registration errors remain catchable by old and new bases."""
    assert issubclass(RegistrationError, RegistryError)
    assert issubclass(RegistrationError, ComponentError)
    assert issubclass(RegistrationError, AgentOSError)


def test_exception_message_and_explicit_chaining_are_preserved() -> None:
    """Domain errors preserve their message and chained lower-level cause."""
    cause = ValueError("invalid provider response")

    with pytest.raises(ModelError) as captured:
        raise ModelError("Model request failed") from cause

    assert str(captured.value) == "Model request failed"
    assert captured.value.__cause__ is cause
