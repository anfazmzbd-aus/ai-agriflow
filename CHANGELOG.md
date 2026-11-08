# Changelog

Notable changes to AgentOS AgriFlow are recorded here. This changelog also serves as
the release notes for each tagged version.

## [0.1.0] — Alpha

Initial Sprint 2 framework release. This is an early, in-process framework and
reference application release, not a production agriculture platform.

### Included

- Typed execution status and `ExecutionResult[T]` contracts, plus the AgentOS
  exception hierarchy.
- Named `BaseComponent` identity and asynchronous lifecycle contracts.
- Generic lifecycle-aware `BaseAgent` execution.
- An in-process asynchronous `EventBus` and name-based `Registry`.
- A typed `ServiceContainer` with instance, singleton-factory, and transient
  registrations.
- `ComponentManager` dependency ordering, startup, rollback, shutdown, and cleanup
  retry behavior.
- Runtime composition and managed component lifecycle operations.
- Runtime integration coverage, runnable examples, and the `agriflow health` CLI.

### Verification

Release verification must be run against the final tagged candidate. Historical
Sprint 2 verification results are recorded in `docs/handoff/STATUS.md` and do not
replace release-candidate verification.

### Known limitations

- ServiceContainer does not initialize, stop, or dispose registered services.
- Direct ComponentManager lifecycle calls bypass Runtime serialization and telemetry.
- Runtime does not drain admitted BaseAgent executions; its public service and
  manager references can be reassigned, breaking core service-binding identity.
- Cancellation can interrupt cleanup, and stopping a `LifecycleComponent` from
  `NEW` skips its stop hook.
- Event delivery is in-process and fail-fast; concurrent publications may interleave.
- Durable workflows, distributed orchestration, and production agricultural
  integrations are not included.

[0.1.0]: https://github.com/anfazmzbd-aus/ai-agriflow/releases/tag/v0.1.0
