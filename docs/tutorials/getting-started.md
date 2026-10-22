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
