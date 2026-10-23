# AgentOS API

`agentos.core.ExecutionResult[T]` is the typed outcome contract. Use its
`success`, `failure`, `timeout`, `partial`, `retry`, or `cancelled` factories.
Successful and partial results carry a value; `has_value` distinguishes an
explicit `None` value from no value. Failed and timeout results require a
non-empty error message. Retry and cancellation messages are optional. Metadata
is copied on construction and returned as a read-only mapping.

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
