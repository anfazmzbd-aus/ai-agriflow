# Baseline verification evidence

Environment: handoff container, Python 3.13.5.

- `python -m pytest -q`: FAIL at collection (`ModuleNotFoundError: agentos`) because the package was not installed in this environment.
- `PYTHONPATH=src python -m pytest -q`: PASS, 6 tests.
- `python -m ruff check .`: NOT RUN (Ruff not installed).
- `python -m mypy src`: NOT RUN (mypy not installed).
- `python -m build --no-isolation`: NOT RUN (build not installed).

**Baseline is partially verified only.** Codex must install development dependencies, run all checks and reconcile against the original repository before approving any task.
