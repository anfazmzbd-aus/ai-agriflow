# Getting Started

Install the development environment:

```bash
uv sync --extra dev
```

Run the quality checks:

```bash
uv run ruff check .
uv run mypy
uv run pytest
```

Run the AgriFlow health check:

```bash
uv run agriflow health
```

Run the examples:

```bash
uv run python examples/hello_agent.py
uv run python examples/simple_workflow.py
uv run python examples/weather_demo.py
```

## Inspect an execution result

Framework components can use `ExecutionResult[T]` to return an explicit outcome
without raising an exception for ordinary execution failures:

```python
from agentos.core import ExecutionResult

result = ExecutionResult[str].success("soil moisture is low")
if result.status.is_success:
    print(result.value)

retry = ExecutionResult[str].retry("weather provider is temporarily unavailable")
```

Successful and partial outcomes carry a value. `has_value` distinguishes a missing
value from a legitimate `None`. Failed and timed-out outcomes require a non-empty
error message. Metadata is copied and exposed as a read-only mapping.
