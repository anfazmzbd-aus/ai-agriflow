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

`agentos.base.Component` remains the abstract component interface.
`agentos.base.BaseComponent` is a concrete implementation that accepts a stable
name at construction. Names must be strings containing at least one non-whitespace
character; valid names are preserved as supplied and exposed through a read-only
property. Lifecycle operations are defined separately from component identity.

### Lifecycle components

`agentos.base.LifecycleComponent` is an opt-in asynchronous base for components that
own resources. Implement `_initialize()`, `_start()`, and `_stop()` hooks; call
`initialize()`, `start()`, and `stop()` to run them. Hooks must not recursively call
the public lifecycle methods. Per-instance synchronization serializes concurrent
calls. Repeated initialization while initialized, start while started, and stop
while stopped are no-ops. Stopping a new component moves it directly to stopped
without invoking cleanup. A failed or cancelled hook leaves the component failed;
`stop()` can then retry cleanup. The original exception or cancellation propagates.

| Current state | Call | Resulting state | Hook |
| --- | --- | --- | --- |
| `NEW` | `initialize()` | `INITIALIZED` | `_initialize()` |
| `INITIALIZED` | `initialize()` | `INITIALIZED` | none |
| `INITIALIZED` | `start()` | `STARTED` | `_start()` |
| `STARTED` | `start()` | `STARTED` | none |
| `NEW` | `stop()` | `STOPPED` | none |
| `INITIALIZED` or `STARTED` | `stop()` | `STOPPED` | `_stop()` |
| `STOPPED` | `stop()` | `STOPPED` | none |
| `FAILED` | `stop()` | `STOPPED` on success; otherwise `FAILED` | `_stop()` |

Starting before initialization, initializing a started component, or initializing/
starting a stopped or failed component raises `AgentOSRuntimeError` without changing
state. An ordinary hook exception or cancellation marks the component failed and is
re-raised unchanged. `KeyboardInterrupt` and `SystemExit` propagate without being
caught or changing lifecycle state. Cancellation while waiting for the transition
lock has no state effect. After a hook returns, the state update runs synchronously
with no intervening await, so cancellation cannot arrive in the gap between hook
success and that transition being recorded.

The states are `NEW`, `INITIALIZED`, `STARTED`, `STOPPED`, and `FAILED`. Stopped is
terminal: components cannot restart. Lifecycle hooks return `None`; operation
outcomes continue to use `ExecutionResult[T]` where appropriate. This contract does
not discover components or coordinate startup order; those concerns belong to a
future component manager/runtime integration.

### Base agents

`agentos.agents.BaseAgent[InputT, OutputT]` is an abstract, lifecycle-aware base for
typed asynchronous agents. Implement `_execute(input)` and override lifecycle hooks
only when resource setup or cleanup is needed. The default hooks are no-ops. Call
`initialize()` and `start()` before `run(input)`; calls to `run()` outside `STARTED`
raise `AgentOSRuntimeError` before execution. Successful calls return the raw typed
output. `AgentError` propagates unchanged; unexpected ordinary exceptions become a
safe `AgentError` chained from the original. Cancellation, `TimeoutError`,
`KeyboardInterrupt`, and `SystemExit` propagate unchanged. No retry or timeout is
performed internally.

The started-state check is an admission check only. A concurrent `stop()` may finish
while `_execute()` is still awaiting; the in-flight call may then complete while the
agent state is `STOPPED`. Execution does not mutate lifecycle state. A
`BaseAgent[AgentContext, AgentResult]` specialization is structurally compatible with
the existing `Agent` protocol; `EchoAgent` and the protocol itself are unchanged.

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
