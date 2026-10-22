# AgentOS / AgriFlow

A reusable DAG-based AI agent runtime and Sri Lankan agriculture/climate-resilience application.

## Handoff status
This is a **reconstructed Codex handoff baseline**, not a copy of the original local repo. `ExecutionStatus` is implemented; the next task is `ExecutionResult[T]`. See `AGENTS.md` and `docs/handoff/STATUS.md`.

## Setup (Python 3.13+)
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
python -m mypy src
python -m build
```

Use `python -m pip install -e ".[dev]"` in PowerShell. Do not advance to the next task without user approval.
