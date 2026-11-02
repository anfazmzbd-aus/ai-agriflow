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
and derives from `RegistryError`; `ServiceError` reports service container
registration or resolution failures. When translating a lower-level exception, use
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

### Event system

`agentos.events.EventBus` dispatches `Event` objects in-process. Subscribe with a
nonblank exact event type or the global wildcard `"*"`; the value is preserved as
provided. Other event-type strings containing `*` are literal names, not patterns.
Each call to `subscribe()` is a separate registration, including repeated
registrations of the same handler. `unsubscribe()` removes the first equal
registration and returns whether it found one. `subscriber_count()` counts exact
registrations only (or global registrations when queried with `"*"`).

Each `publish()` snapshots its handlers before callbacks begin, runs exact handlers
in registration order, then global wildcard handlers in registration order, and
awaits each sequentially. Subscription changes during dispatch affect future
publishes only. A handler exception propagates unchanged and stops later handlers;
cancellation also propagates and stops dispatch. Publishing with no subscribers is
a successful no-op. Concurrent publishes are independent and may interleave; the
bus does not provide cross-publication ordering or thread-safety guarantees.

`Event.type` must be a nonblank string and valid values are preserved exactly. Event
instances and payloads remain mutable for compatibility. Payloads are in-process
Python data, are passed to handlers without serialization or deep copying, and may
be mutated by handlers. External broker serialization, persistence, retries, and
background delivery are outside this API.

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

### Service container

`agentos.container.ServiceContainer` maps Python class objects to explicit service
instances or synchronous factories. Class keys may be concrete classes, abstract
classes, or Protocols. Factories receive the container and may call `resolve()` for
their dependencies. Registration is unique; duplicate keys raise `ServiceError`.
Instances preserve identity. Factories default to lazy singleton lifetime and may
select `lifetime="transient"` to construct a new result for each resolution.
Singleton results are cached only after successful, non-`None` construction.

`resolve(ServiceType)` returns the generic type declared by that key. This is a
static typing contract; the container does not use runtime `isinstance()` checks.
Because MyPy models `type[T]` as a constructible class, Protocol and abstract-class
tokens need an explicitly typed `type[Interface]` cast/alias at the registration
site; resolving through that typed token retains the interface result type.
Missing registrations and direct or indirect circular dependencies raise
`ServiceError`. Factory exceptions propagate unchanged, and failed singleton
construction can be retried. `None` instances and `None` factory results are
rejected. There is no replacement API.

Registration and resolution are synchronous and serialized by a per-container
reentrant lock. This ensures a singleton factory is successfully run at most once,
including concurrent resolution. Factories should be short-running and must not
synchronously wait for another thread that needs the same container. Async factories
and awaitable factory results are unsupported. The container does not initialize,
stop, or dispose services; it is independent of `Registry`, `Runtime`, and `EventBus`.
