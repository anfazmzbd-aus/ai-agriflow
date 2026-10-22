# ADR 0002: Sprint 2 Framework Primitives

## Status

Accepted

## Context

Sprint 2 needs production-ready code for the framework seams established during bootstrap:
runtime composition, event delivery, workflow execution, tool invocation, memory, model
messages, registry, adapters, and telemetry.

## Decision

Implement deterministic in-process primitives first. These components are small, typed,
documented, and tested, giving later sprints stable contracts before adding distributed
storage, external model providers, durable queues, or full LangGraph compilation.

## Consequences

The repository now has runnable framework behavior with minimal operational complexity.
Future integrations can replace the in-memory implementations without changing the public
contracts used by examples and applications.
