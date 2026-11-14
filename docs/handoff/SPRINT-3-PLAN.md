# Sprint 3 — Initial Planning Proposal

**DRAFT — NOT APPROVED**
**Prepared:** 2026-11-13
**Status:** Proposal only. No Sprint 3 implementation is authorized or started.

## Sprint objective

Propose the next increment for AgentOS: deterministic in-process DAG workflow execution built on the released Sprint 2 foundations. Keep AgentOS independent of AgriFlow application code and vendor-specific orchestration APIs. Use AgriFlow only as a small reference application with mocked boundaries.

Before each task, inspect the actual APIs and consumers at the selected baseline. This is an initial backlog, not a substitute for task-specific architecture review or acceptance approval.

## Proposed numbered tasks and sequence

### 3.1 — Workflow graph model and validation

**Depends on:** Sprint 2 release baseline.

Define typed node/edge identities and a graph representation. Validate duplicate or missing identifiers, missing dependencies, and cycles. Produce deterministic topological order. This task validates graphs only; it does not execute them.

**Acceptance:** valid DAGs produce stable order; malformed and cyclic graphs fail with documented errors; graph behavior has positive, negative, boundary, and regression tests; no external orchestration dependency is added.

### 3.2 — Workflow execution context and node contract

**Depends on:** 3.1.

Define the smallest typed context and node execution contract needed to pass inputs/results between graph nodes. Specify state ownership, result retention, error representation, and safe diagnostic behavior.

**Acceptance:** public types are documented and mypy-checked; success and failure states map consistently to existing ExecutionResult[T] and AgentOSError contracts; no application-specific types enter core.

### 3.3 — Sequential asynchronous DAG executor

**Depends on:** 3.1 and 3.2.

Implement deterministic sequential execution first. Execute nodes only after dependencies succeed; define fail-fast behavior, partial results, cancellation propagation, and cleanup boundaries. Do not add parallel scheduling in this task.

**Acceptance:** independent nodes follow documented stable ordering; dependency failures prevent downstream execution; results and causes are preserved; cancellation and ordinary exceptions follow explicit tested policies; no hidden retries or implicit timeouts.

### 3.4 — Runtime-managed workflow execution

**Depends on:** 3.3.

Review Runtime and ComponentManager ownership before adding the narrowest execution entry point. Preserve existing constructor and lifecycle compatibility. Do not turn Runtime into a service locator or duplicate ComponentManager responsibilities.

**Acceptance:** workflow execution uses the approved lifecycle/runtime boundary; repeated and concurrent calls have documented semantics; failures do not leave lifecycle state inconsistent; existing Runtime and manager tests remain valid.

### 3.5 — Framework adapters for agents and tools

**Depends on:** 3.2 and 3.3.

Add minimal adapters so existing Agent and Tool contracts can be used as workflow nodes. Keep vendor-specific integrations behind separate adapters and do not couple core to LangGraph.

**Acceptance:** typed input/output flow is checked; errors retain causes; adapters have unit and integration tests; Agent/Tool public APIs remain backward compatible.

### 3.6 — AgriFlow reference workflow

**Depends on:** 3.4 and 3.5.

Demonstrate a small agriculture/climate-resilience workflow using deterministic fake data and injected services. Keep external weather, soil, model, and agricultural APIs out of tests and core.

**Acceptance:** runnable local example; mocked/injected boundaries; no secrets or network dependency; user-facing output clearly identifies itself as a reference/demo result.

### 3.7 — System validation and handoff

**Depends on:** 3.1–3.6.

Add end-to-end coverage across graph validation, runtime execution, agents/tools, and failure recovery. Reconcile API/architecture documentation and record supported limitations.

**Acceptance:** full suite and quality gates pass; repository coverage remains at least 80%; package builds offline; no skipped/xfail tests to conceal defects; remaining risks are documented. Release preparation, tagging, and publication require separate approval.

## Cross-task dependencies

Sequence is intentionally conservative: graph validation → execution contracts → sequential executor → Runtime integration → adapters → reference workflow → system validation. If source inspection finds overlapping existing abstractions, revise the proposal before implementation approval.

## Testing and verification requirements

For each separately authorized task, use the repository's uv-managed environment and locked dependencies. At minimum, run task-focused tests, the complete pytest suite with the 80% repository coverage gate, Ruff lint, Ruff formatting, MyPy, and an offline package build. Add deterministic tests for invalid graphs, failures, cancellation, concurrency boundaries, and backward compatibility as relevant. Run documentation validation when the repository configuration supports it. Record exact commands, interpreter, exit codes, and whether evidence is Codex-, user-, or CI-executed.

## Known risks

- Workflow state and node output may contain credentials or sensitive application data; diagnostics must not leak values.
- Cancellation, rollback, and lifecycle cleanup interact with existing documented limitations.
- Sequential execution simplifies determinism but may constrain throughput; parallel scheduling needs its own design and bounded concurrency policy.
- Runtime, ComponentManager, BaseAgent, EventBus, and ServiceContainer already have defined ownership boundaries; avoid duplicate orchestration responsibilities.
- The repository is a reconstructed handoff baseline. Confirm real source contracts and consumers before changing public APIs.
- The 2026-11-11 OSV result is limited to its scanner/database snapshot and does not replace ongoing dependency review.

## Explicitly out of scope

- Sprint 3 implementation before separate authorization.
- Parallel/distributed execution, persistence, retries by default, or a workflow service/queue.
- Production deployment, cloud resources, production credentials, or public agricultural integrations.
- LangGraph-specific core imports or model-vendor coupling.
- New dependencies, lockfile changes, or public API changes without task-specific review and approval.
- Release tags, GitHub Releases, and package registry publication without separate authorization.

## Approval gates

1. This document is a draft proposal only.
2. Task 2.13 documentation must be reviewed and separately approved for commit.
3. Sprint 3 planning must receive explicit authorization.
4. Each numbered Sprint 3 task requires its own scope, design, acceptance criteria, and implementation approval before code changes.
5. Each task requires verification, diff review, and explicit commit approval; commit approval does not authorize the next task.
