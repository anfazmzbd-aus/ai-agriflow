# Task register

| Task | Description | Status | Gate |
| --- | --- | --- | --- |
| 2.3.1 | ExecutionStatus enum, helpers and tests | Baseline reconstructed | Verify against user's local repo |
| 2.3.2 | Generic ExecutionResult[T], invariants, factories, tests and exports | Committed `9c79638`; user-verified | Complete |
| 2.3.3 | Core exception hierarchy | Committed; user-verified | Complete |
| 2.4 | BaseComponent | Committed `7338f51`; user-verified | Complete |
| 2.5 | Lifecycle contracts | User-verified; merged as `57f9383` | Complete |
| 2.6 | BaseAgent | Verified; merged as `c34c19b` | Complete |
| 2.7 | Event system | Committed `45482d4`; pushed; verified; merged as `2ad392f` | Complete |
| 2.8 | Service container | Committed `168be89`; pushed; verified; merged as `779dae2` | Complete |
| 2.9 | Component manager | Committed `f5f7224`; pushed; verified; merged as `26313e5` | Complete |
| 2.10 | Runtime | Committed; pushed; verified; merged as `d6afa8a` | Complete |
| 2.11 | Integration tests | Committed `20129d0c42c7eddaf17c99426cc2f94c21f3854c`; merged as `8daf6db6e7685ddc2ac2eaa278525f948d075705` | Complete; PR #7 CI passed before merge |
| 2.12 | Sprint release | Complete — published and verified | GitHub pre-release v0.1.0, Release ID 443538987; tag target is 073bfb796e473715f1b42f99aa32afe32fdfda1c; workflow 43287980180 passed; two assets SHA-256 verified. See post-release closure in STATUS.md. |
| 2.13 | Post-release handoff documentation | Complete — PR #9 merged | Main merge commit cd9a6c35203bb4c2c7a2dc5d71cacec7a861afcf. |
| 3.1 | Workflow graph model and validation | Merged via PR #10 | Main merge 4dd8bba682a4a6967d87b88ac62de9e73315b7ca; post-merge CI 44008844894 verify passed. |
| 3.2 | Workflow execution context and node contract | Technically verified; not staged or committed | Windows: 60 focused / 282 full tests, 98.02% coverage; quality, typing, docs, offline build and installed-wheel acceptance passed. Final review and explicit staging/commit approval required. |

## Task 2.9 acceptance criteria

- Explicit asynchronous lifecycle coordination for registered `LifecycleComponent`s.
- Stable named dependency ordering, complete graph and component-state preflight,
  initialize-all-before-start, and reverse-order shutdown/rollback.
- Serialized lifecycle operations, same-task reentrancy protection, deterministic
  cancellation and process-control handling, ordinary failure aggregation, and
  cleanup retry from `FAILED`.
- No modifications to Runtime, Registry, ServiceContainer, LifecycleComponent,
  BaseAgent, EventBus, dependency declarations, or `uv.lock`.
- Implementation remains on `feat/2.9-component-manager` based on Task 2.8 merge
  `779dae278a9eb6015bb1791c0090d08a201eef93`.

## Task 2.3.2 acceptance criteria (proposal; confirm before implementation)
- Typed generic result contract; explicit semantics for success/failure/partial/retry.
- No shared mutable metadata defaults; predictable error handling.
- Positive/negative/boundary tests, type checking, public exports, usage example and docs.
- All applicable checks pass, results documented; user reviews before commit.

## Sprint 2 closure

Sprint 2 is administratively closed after publication of the v0.1.0 Alpha GitHub pre-release. This does not authorize implementation work in Sprint 3.

## Sprint 3 proposal

**Historical planning checkpoint:** Sprint 3 was **proposed, not started** at the Task 2.13 closure. The initial backlog remains in [SPRINT-3-PLAN.md](SPRINT-3-PLAN.md), marked DRAFT — NOT APPROVED.

**Historical checkpoint (2026-11-16):** Task 3.1 received separate architecture and implementation authorization and is implemented and technically verified, pending final diff review and commit authorization. The baseline remains `cd9a6c35203bb4c2c7a2dc5d71cacec7a861afcf`, with detached HEAD. The nine-path candidate excludes the known generated `site/` output. Task 3.2 has not started and requires separate authorization. Each numbered task retains its own planning/implementation, verification, and commit gates; Task 3.1 approval does not approve the rest of the draft plan.

## Task 3.2 current checkpoint — 2026-11-17

Architecture, implementation, and verification were separately approved. The
candidate is based on Task 3.1 merge 4dd8bba682a4a6967d87b88ac62de9e73315b7ca.
Acceptance requires independent run stores, record-once identity retention,
immutable snapshots, direct dependency views, explicit None semantics, all six
existing statuses, safe diagnostics, typed asynchronous handlers, and unchanged
linear workflow behavior. Verification evidence is recorded in STATUS.md.
Task 3.3, staging, commit, push, and PR creation are not authorized.

Verification: the new context module has 100% statement/branch coverage. Positive
MyPy passed; nine expected negative errors were verified by the assertion harness.
See STATUS.md for exact commands, actual exits, earlier findings and repairs,
packaging checksums, and privacy/concurrency limits. No next task is authorized.
