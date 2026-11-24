# Architecture Overview

The repository is split into two primary layers:

1. `src/agentos/` provides reusable framework capabilities.
2. `apps/agriflow/` composes framework capabilities into the AgriFlow application.

The framework is intentionally modular so future sprints can add runtime orchestration,
events, tools, agents, memory, model adapters, telemetry, and plugin registration without
reshaping the repository.

## Sprint 2 Components

- `base` defines common component contracts and framework exceptions.
- `base.lifecycle` provides an opt-in asynchronous lifecycle contract; identity-only
  components remain lifecycle-free.
- `manager` coordinates explicitly registered lifecycle components in dependency order.
- `events` provides a deterministic sequential in-process event bus with exact and
  global-wildcard subscriptions.
- `registry` provides name-addressable component registration.
- `container` provides explicit type-keyed service registration and synchronous
  dependency resolution; it does not own lifecycle or disposal.
- `tools` wraps asynchronous Python callables as AgentOS tools.
- `agents` defines the backward-compatible agent protocol and deterministic echo
  agent, plus a generic lifecycle-aware `BaseAgent` for typed async execution.
- `memory` provides an in-process memory store.
- `models` defines chat request/response primitives and a deterministic echo model.
- `workflows` runs ordered asynchronous workflow steps and validates immutable DAG topology.
- `adapters` defines the LangGraph adapter boundary.

Workflow graphs describe prerequisites between graph-local node IDs. Graph validation
and ordering are synchronous and independent of the runtime and lifecycle manager.
The ready node declared earliest is selected at every topological step. Component
dependencies continue to govern lifecycle startup and shutdown independently.
- `telemetry` records structured runtime events.
- `runtime` composes settings, events, registry, telemetry, typed services, and the
  component lifecycle manager.

## Component lifecycle boundary

`Component` and `BaseComponent` define identity only. Components that acquire
resources can opt into `LifecycleComponent`, whose per-instance lock serializes
initialize/start/stop transitions and whose hooks report failure by raising. It does
not perform discovery or cross-component coordination. `ComponentManager` provides
explicit dependency ordering and lifecycle coordination around this contract. Runtime
composes a manager with services, events, registry, settings, and telemetry, but does
not discover components or inject application services automatically. Applications
register lifecycle components and service instances explicitly and resolve/inject
application dependencies themselves.

`BaseAgent` opts into `LifecycleComponent`, requires `STARTED` as an execution
admission check, and returns the raw typed result. It does not coordinate in-flight
execution with shutdown: a concurrent stop may finish while a run is awaiting. Agent
implementations and future adapters own provider-specific behavior; the base class
does not depend on Runtime, EventBus, ServiceContainer, or LangGraph.

`ComponentManager` accepts explicit `LifecycleComponent` instances and named lifecycle
dependencies. It validates the full dependency graph and all initial component states
before invoking hooks, initializes every component in stable topological order, then
starts them in the same order. Shutdown and rollback run in reverse topological order.
An asyncio lock serializes manager lifecycle calls; recursive calls from a component
hook raise `AgentOSRuntimeError`. Registration closes after graph/state preflight and
before lifecycle hooks begin; attempts to register during an active operation fail.
The manager aggregates ordinary rollback and cleanup errors, propagates cancellation
and process-control exceptions without wrapping, and retries cleanup on a later
`stop()` call while failed. It does not construct components, integrate with Runtime,
EventBus, or ServiceContainer, or drain in-flight BaseAgent executions. Cancellation
or repeated interruption can prevent best-effort cleanup from finishing; another
`stop()` call is required to retry remaining component cleanup. Since the existing
`LifecycleComponent.stop()` skips its hook from `NEW`, a process-control exception
during initialization cannot invoke cleanup for that still-new component through
the public lifecycle API.

`EventBus` snapshots matching registrations at publication start and runs exact
handlers before wildcard handlers, sequentially. A handler failure or cancellation
stops that publication; concurrent publications may interleave. The bus is
in-memory only and does not serialize events or provide persistence, retries, or
distributed delivery.

`Runtime` preserves its legacy synchronous `start()` operation for logging and the
historical `runtime.started` telemetry event. Managed orchestration uses the separate
`initialize_async()`, `start_async()`, and `stop_async()` methods. Runtime delegates
state, ordering, rollback, and cleanup to `ComponentManager`; it does not create a
second lifecycle state machine. Managed lifecycle telemetry is best-effort and emitted
after transitions. EventBus is not used for lifecycle notifications. Runtime serializes
its managed entry points and rejects recursive calls. It does not drain active agent
executions. Its public `services` and `component_manager` fields must not be replaced
after construction because Runtime's other fields and type bindings retain their
original object identities.

`ServiceContainer` is separate from the name-based `Registry`. It resolves explicit
class, abstract-class, and Protocol keys through instances or synchronous factories.
Singleton creation is lazy and serialized by a per-container reentrant lock;
transient factories run for each resolution. The container detects recursive
dependency cycles but does not scan constructors, manage lifecycle, dispose services,
or integrate with Runtime yet.

## DAG execution contracts (Task 3.2)

`WorkflowRunState[InputT]` owns an independent in-process result store for a
validated graph. It exposes read-only result snapshots and creates immutable
`WorkflowNodeContext[InputT]` views of direct prerequisites.
`WorkflowNodeHandler[InputT, OutputT]` is an asynchronous callable returning the
existing `ExecutionResult[OutputT]`.

The existing linear `WorkflowContext` carries replacement state between steps.
Extending it would mix state replacement with graph-scoped result ownership, so
the DAG view is distinct and does not inherit from or alter that contract. Giving
handlers the mutable run owner was rejected because it would permit accidental
overwrites and expose unrelated results.

Graph topology remains Task 3.1. Contexts and retention are Task 3.2. Handler
binding, scheduling, invocation, and status-based failure policy belong to Task
3.3; lifecycle admission belongs to Task 3.4. No runtime, manager, agent/tool, or
vendor adapter dependency enters these contracts.

The owner assumes one coordinator. Structural snapshots do not freeze arbitrary
payload objects. Inputs and nested values are borrowed immutable-by-convention
references, and homogeneous run input typing does not establish heterogeneous
dependency output types. The implementation preserves original outcome identity
while erasing its output type only at the private storage boundary.

## Sequential DAG execution (Task 3.3)

`WorkflowNodeBinding[InputT]` keeps topology separate from executable handlers.
Its generic constructor accepts each concrete output type, then privately erases
it for heterogeneous storage. An ordered binding sequence allows duplicate
declarations to be rejected rather than silently overwritten by dictionary input.

`SequentialWorkflowExecutor[InputT]` snapshots bindings, consumes the existing
stable graph order, and creates one independent run store per admitted invocation.
It awaits each handler directly and stops globally at the first non-success.
Read-only progress/final snapshots preserve completed results when errors or
actual cancellation propagate. One active run per executor is enforced without
queueing callers; separate instances may run concurrently.

A stateless function was rejected because cancellation would otherwise lose
access to retained outcomes. A separate run-handle/report hierarchy was deferred
to keep the public interface small. Existing ExecutionResult aggregates as
SUCCESS when all nodes succeed and PARTIAL when a returned non-success leaves
outcomes available. Original node outcomes are retained inside the result map.
Raised errors remain a distinct exception channel with safe chained summaries.

Task 3.1 owns graph validation, Task 3.2 owns context and result storage, and
Task 3.3 owns invocation and fail-fast policy. Task 3.4 retains Runtime integration;
Task 3.5 retains Agent/Tool adapters. ComponentManager lifecycle ordering, cleanup,
and Runtime admission are unchanged. No executor lifecycle ownership is implied.
