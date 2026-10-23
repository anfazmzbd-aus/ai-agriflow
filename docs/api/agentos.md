# AgentOS API

`agentos.core.ExecutionResult[T]` is the typed outcome contract. Use its
`success`, `failure`, `timeout`, `partial`, `retry`, or `cancelled` factories.
Successful and partial results carry a value; `has_value` distinguishes an
explicit `None` value from no value. Failed and timeout results require a
non-empty error message. Retry and cancellation messages are optional. Metadata
is copied on construction and returned as a read-only mapping.

AgentOS framework exceptions are rooted at `AgentOSError` and exported from
`agentos.base`. `ComponentError` groups operational component failures;
`ConfigurationError` represents invalid configuration. Domain errors include
`AgentOSRuntimeError`, `WorkflowError`, `AgentError`, `ToolError`, `ModelError`,
`AgentOSMemoryError`, and `RegistryError`. `RegistrationError` remains available
and derives from `RegistryError`. When translating a lower-level exception, use
`raise DomainError("safe summary") from exc` to retain the original cause. Keep
credentials and secret values out of exception messages.

::: agentos

::: agentos.core

::: agentos.runtime

::: agentos.events

::: agentos.registry

::: agentos.tools

::: agentos.agents

::: agentos.memory

::: agentos.models

::: agentos.workflows

::: agentos.adapters

::: agentos.telemetry
