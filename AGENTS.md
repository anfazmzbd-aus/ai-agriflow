# AgentOS / AgriFlow — Codex Operating Contract

## Mission and boundaries
Build AgentOS, a reusable Python DAG-based AI agent runtime, with AgriFlow as its Sri Lankan agriculture/climate-resilience reference application. Keep the framework independent of the application and of LangGraph-specific APIs; use adapters.

## Current checkpoint
Sprint 2, Task 2.3.1 (`ExecutionStatus`) is the handoff baseline. **Next proposed task: 2.3.2 `ExecutionResult[T]`.** This repository contains a reconstructed baseline, not an import of the user's original local repository. Inspect and reconcile any existing implementation before applying changes.

## Mandatory gated workflow
1. Read `docs/handoff/STATUS.md`, `docs/handoff/TASKS.md`, and inspect `git status` and recent commits.
2. Work on exactly ONE numbered task at a time. Before editing, state scope, acceptance criteria, tests, risks, and files to change.
3. Implement production code, matching tests, package exports, example where appropriate, and relevant docs.
4. Run task-specific tests, then full tests, Ruff, mypy, and any applicable build/integration checks. Record actual commands, exit codes and outcomes. Never claim unrun checks passed.
5. Review diff, security, typing, failure paths, backward compatibility, and coverage gaps. Update `docs/handoff/STATUS.md` with evidence.
6. **STOP and request explicit human confirmation.** Passing tests does NOT authorize the next task. Do not commit a task implementation until the user approves the verified diff. Approval to commit one task does not authorize beginning another.
7. After approval, commit only the approved task with `task(2.3.2): ...` style message. Show commit hash and clean/dirty status. STOP again; begin next task only upon separate explicit user instruction.
8. On any failed verification, fix within the same task and rerun checks; never bypass tests, weaken assertions, or silently change acceptance criteria.

## Engineering standards
- Python >=3.13; src layout; typed public APIs; `from __future__ import annotations`.
- Small cohesive modules; standard library for core contracts where practical.
- No secrets in source or Git. No network/paid APIs in unit tests. Mock external integrations.
- Use pytest, Ruff and mypy; no skipped tests without a documented reason and approval.
- Each new behavior must have positive, negative, boundary and regression tests as applicable.
- Each task has independent acceptance criteria and reproducible verification evidence.
- Framework must not import from `apps/agriflow`; isolate LangGraph in adapters.
- Avoid force pushes, rebases of shared branches, destructive resets and unapproved dependency upgrades.
- Never create or modify release signing, cloud resources or production credentials without approval.

## Commit policy
Baseline/bootstrap commits may be prepared for this handoff. Subsequent task implementation commits require explicit approval. Never claim user approval based on silence.

## How to report at the gate
Report: task ID, changed files, implementation summary, commands/results, uncovered risks, `git diff --stat`, and exactly what approval is requested. Ask: **Approve committing this task?**
