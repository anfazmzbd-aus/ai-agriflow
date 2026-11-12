# Getting Started

AgentOS AgriFlow requires Python 3.13 or newer. Install the locked development
environment with uv from the repository root:

```bash
uv sync --locked --extra dev
```

The lockfile pins the resolved project and development dependencies. Run the full
test suite (including integration and example tests), and the focused integration
suite when diagnosing application composition:

```bash
uv run pytest -q
uv run pytest tests/integration -q --no-cov
uv run pytest tests/e2e -q --no-cov
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Run the AgriFlow reference CLI health check:

```bash
uv run agriflow health
```

## Compose a runtime

Create a Runtime from settings, register a lifecycle component, then use the
asynchronous managed lifecycle. The Runtime owns its ServiceContainer and
ComponentManager; services must be registered explicitly, and component
dependencies determine initialization/start ordering:

```python
runtime = Runtime.from_settings()
runtime.services.register_instance(WeatherClient, weather_client)
runtime.register_component(weather_component)

await runtime.initialize_async()
await runtime.start_async()
try:
    # Run application work while the managed components are started.
    ...
finally:
    await runtime.stop_async()
```

Import `Runtime` from `agentos.runtime`. `WeatherClient` and `weather_component`
stand for application-provided types and objects; AgentOS does not discover or
construct them automatically. See the API and architecture documentation for the
full lifecycle and service contracts.

Runtime shutdown does not wait for already admitted BaseAgent executions. Direct
calls to `runtime.component_manager` bypass Runtime-level serialization and
telemetry, and ServiceContainer does not dispose services. Coordinate application
work and resource cleanup accordingly.

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
