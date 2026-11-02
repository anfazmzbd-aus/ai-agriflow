from __future__ import annotations


class AgentOSError(Exception):
    """Base exception for all AgentOS framework failures."""


class ComponentError(AgentOSError):
    """Raised when a framework component cannot complete an operation."""


class AgentOSRuntimeError(ComponentError):
    """Raised when the AgentOS runtime cannot start or continue running."""


class RegistryError(ComponentError):
    """Raised when a registry operation cannot be completed."""


class ServiceError(ComponentError):
    """Raised when a service registration or resolution cannot be completed."""


class RegistrationError(RegistryError):
    """Raised when a registry operation is invalid."""


class WorkflowError(ComponentError):
    """Raised when workflow execution fails."""


class AgentError(ComponentError):
    """Raised when agent execution fails."""


class ToolError(ComponentError):
    """Raised when a tool invocation fails."""


class ModelError(ComponentError):
    """Raised when a model operation fails."""


class AgentOSMemoryError(ComponentError):
    """Raised when an AgentOS memory operation fails."""


class ConfigurationError(AgentOSError):
    """Raised when AgentOS configuration is invalid or unusable."""
