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

## Understand DAG context ownership

**WHY:** node handlers need prerequisite outcomes without receiving a mutable
global store. **WHAT:** use a run owner for retention, a node context for input,
and an asynchronous callable returning `ExecutionResult[T]`.
**HOW:** declare topology first, record outcomes explicitly, and request a view.

**IMPLEMENT:** `examples/workflow_context.py` demonstrates a manual handler call;
it is not a DAG executor. Run it locally with:

```console
uv run --locked --no-sync python -m examples.workflow_context
```

Expected output is `reference: 7`. It uses no external services.
`record_result` preserves the outcome object, and `context_for` filters results
to direct dependencies in their declared order. The example narrows an
`object` value with `isinstance` before consuming it.

**TEST:** focused workflow tests check isolated stores, snapshots, all six statuses,
None values, direct visibility, safe diagnostics, and exception propagation.
Static contract tests assert both accepted handlers and exact expected MyPy
rejections. Full repository coverage must remain at least 80%.

**EXPLAIN THE CODE:** frozen context fields and read-only maps protect structure.
They do not deep-copy nested payloads. Use `has_value` to distinguish absent
values from `ExecutionResult[None].success(None)`. A RETRY outcome is retained
without causing a retry. Ordinary exceptions and cancellation are not normalized.

**EXERCISE (optional, not a production change):** make the recorded root outcome
a successful None and adapt the example to report it without treating it as a
missing result. Then demonstrate how a shared list can still change inside a
read-only snapshot.

**INTERVIEW QUESTIONS:** Why does a node ID not prove its output type? Why should
result storage avoid deciding which status makes another node runnable? Why can
printing a full exception chain disclose information despite a safe outer message?
