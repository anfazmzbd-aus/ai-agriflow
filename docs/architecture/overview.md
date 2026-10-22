# Architecture Overview

The repository is split into two primary layers:

1. `src/agentos/` provides reusable framework capabilities.
2. `apps/agriflow/` composes framework capabilities into the AgriFlow application.

The framework is intentionally modular so future sprints can add runtime orchestration,
events, tools, agents, memory, model adapters, telemetry, and plugin registration without
reshaping the repository.

## Sprint 2 Components

- `base` defines common component contracts and framework exceptions.
- `events` provides an asynchronous in-process event bus.
- `registry` provides name-addressable component registration.
- `tools` wraps asynchronous Python callables as AgentOS tools.
- `agents` defines the agent protocol and a deterministic echo agent.
- `memory` provides an in-process memory store.
- `models` defines chat request/response primitives and a deterministic echo model.
- `workflows` runs ordered asynchronous workflow steps.
- `adapters` defines the LangGraph adapter boundary.
- `telemetry` records structured runtime events.
- `runtime` composes settings, events, registry, and telemetry.
