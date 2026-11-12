# AgentOS AgriFlow Platform

AgentOS AgriFlow is an early-stage Python framework and reference application for agentic
workflows. The AgriFlow application is a development reference, not a production agriculture
product.

## Version

Current candidate version: `0.1.0` (Alpha). It is not yet tagged or published.

## Stack

- Python >=3.13
- uv for dependency management
- Hatchling for packaging
- Pydantic v2 and Pydantic Settings v2
- structlog for structured logging
- LangGraph and LangChain Core for workflow orchestration
- pytest, Ruff, and mypy for quality gates
- MkDocs Material for documentation
- Docker and GitHub Actions tooling

## Quick Start

```bash
uv sync --locked --extra dev
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv build
```

Run either supported application CLI form:

```bash
uv run agriflow
uv run agriflow health
```

## Sprint 2 and Release Status

As of 2026-11-11, Sprint 2 Task 2.11 is merged into `main`; Task 2.12 is the current
release-preparation task. Draft [PR #8](https://github.com/anfazmzbd-aus/ai-agriflow/pull/8)
contains the `v0.1.0` Alpha candidate. The critical certifi fix updates `2026.7.22` to
`2026.10.23`. An offline OSV scan of the refreshed 2026-11-11 PyPI snapshot reconciled
all 82 third-party locked packages and found no matching advisories. GitHub Actions passed
for security commit `119670afc9ec68a643c40808884f29a7e27406ab`. PR review/merge and separate
release approvals remain pending; the version is not tagged or published and is not
production-ready.

## Known Limitations

- Runtime does not drain in-flight BaseAgent executions, and its public manager and
  service references can be reassigned, breaking core service-binding identity.
- Direct ComponentManager calls bypass Runtime serialization and telemetry. Cancellation
  can interrupt lifecycle cleanup, and stopping a component from `NEW` skips its stop hook.
- Event delivery is in-process and fail-fast; concurrent publications may interleave.
- The wheel contains the `agentos` and `apps` packages; examples and documentation are
  available from the source distribution or repository, not the wheel.
- Durable workflows, distributed orchestration, and production agricultural integrations
  are not included.

## Repository Layout

- `src/agentos/` contains the reusable framework.
- `apps/agriflow/` contains the AgriFlow application.
- `examples/` contains runnable examples.
- `tests/` contains unit, integration, and end-to-end tests.
- `docs/` contains architecture, ADRs, tutorials, and API documentation.

## Development Standards

- Every Python file starts with `from __future__ import annotations`.
- Public APIs require type hints and docstrings.
- Production modules should have corresponding tests.
- Architectural decisions live in `docs/adr/`.

> **Repository fidelity:** This is a reconstructed handoff baseline and may not match the
> original local project. Reconcile its history, source layout, `pyproject.toml`, and
> `uv.lock` before treating it as a migration or replacing files in an original checkout.

## Branching

- `main` stays stable.
- Feature branches may use names such as `feature/runtime` or `feature/event-bus`.
- Sprint releases should be tagged as `v0.1.0`, `v0.2.0`, and onward.
