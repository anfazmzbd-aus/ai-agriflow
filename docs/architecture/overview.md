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
- `events` provides an asynchronous in-process event bus.
- `registry` provides name-addressable component registration.
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
not perform discovery, dependency ordering, or cross-component coordination. A
future component manager or runtime can build those capabilities around the contract.

`BaseAgent` opts into `LifecycleComponent`, requires `STARTED` as an execution
admission check, and returns the raw typed result. It does not coordinate in-flight
execution with shutdown: a concurrent stop may finish while a run is awaiting. Agent
implementations and future adapters own provider-specific behavior; the base class
does not depend on Runtime, EventBus, ServiceContainer, or LangGraph.
