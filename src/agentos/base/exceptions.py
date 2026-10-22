from __future__ import annotations


class AgentOSError(Exception):
    """Base exception for all AgentOS framework failures."""


class ComponentError(AgentOSError):
    """Raised when a framework component cannot complete an operation."""


class RegistrationError(ComponentError):
    """Raised when a registry operation is invalid."""


class WorkflowError(ComponentError):
    """Raised when workflow execution fails."""
