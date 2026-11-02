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
- `workflows` runs ordered asynchronous workflow steps.
- `adapters` defines the LangGraph adapter boundary.
- `telemetry` records structured runtime events.
- `runtime` composes settings, events, registry, and telemetry.

## Component lifecycle boundary

`Component` and `BaseComponent` define identity only. Components that acquire
resources can opt into `LifecycleComponent`, whose per-instance lock serializes
initialize/start/stop transitions and whose hooks report failure by raising. It does
not perform discovery or cross-component coordination. `ComponentManager` provides
explicit dependency ordering and lifecycle coordination around this contract; Runtime
integration remains a later composition step.

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

`ServiceContainer` is separate from the name-based `Registry`. It resolves explicit
class, abstract-class, and Protocol keys through instances or synchronous factories.
Singleton creation is lazy and serialized by a per-container reentrant lock;
transient factories run for each resolution. The container detects recursive
dependency cycles but does not scan constructors, manage lifecycle, dispose services,
or integrate with Runtime yet.
