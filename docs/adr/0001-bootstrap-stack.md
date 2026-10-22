# ADR 0001: Bootstrap Stack

## Status

Accepted

## Context

The project needs a production-ready foundation for framework development, application
implementation, testing, examples, documentation, CI/CD, and future plugin support.

## Decision

Use Python 3.13, uv, Hatchling, Pydantic v2, Pydantic Settings v2, structlog, pytest,
Ruff, mypy, LangGraph, LangChain Core, httpx, Typer, MkDocs Material, Docker, and GitHub
Actions.

## Consequences

The repository starts with modern Python conventions, reproducible development workflows,
strict quality gates, and a layout that supports sprint-by-sprint expansion.
