# AgentOS AgriFlow Platform

AgentOS AgriFlow is a production-oriented Python repository for building agentic workflows,
starting with an agricultural operations application and a reusable AgentOS framework.

## Version

Current bootstrap version: `0.1.0`.

## Stack

- Python 3.13
- uv for dependency management
- Hatchling for packaging
- Pydantic v2 and Pydantic Settings v2
- structlog for structured logging
- LangGraph and LangChain Core for workflow orchestration
- pytest, Ruff, and mypy for quality gates
- MkDocs Material for documentation
- Docker and GitHub Actions for deployment readiness

## Quick Start

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy
```

Run the application CLI:

```bash
uv run agriflow health
```

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

## Branching

- `main` stays stable.
- Feature branches may use names such as `feature/runtime` or `feature/event-bus`.
- Sprint releases should be tagged as `v0.1.0`, `v0.2.0`, and onward.
