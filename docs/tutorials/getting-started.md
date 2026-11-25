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

## Run a sequential DAG

**WHY:** graph order alone does not invoke handlers or define failure behavior.
**WHAT:** bind typed handlers to graph IDs and run a SequentialWorkflowExecutor.
**HOW:** use one binding per node; handler return values use ExecutionResult[T].

**IMPLEMENT:** the deterministic example uses no paid or agricultural API:

```console
uv run --locked --no-sync python -m examples.sequential_workflow
```

Expected output: `reference result: 14`. The graph declares the reporting node
before collection, but its dependency puts collection first. The example binds
integer and string outputs without caller casts and narrows the dependency value
before consuming it.

**TEST:** executor tests cover complete preflight, stable order, all six outcomes,
global fail-fast, exception causes, actual versus returned cancellation, cleanup,
repeated runs, admission, privacy and old API compatibility. Static fixtures check
both valid heterogeneous bindings and exact expected rejection diagnostics.

**EXPLAIN THE CODE:** run creates a fresh store and awaits handlers in cached
topological order. Only SUCCESS continues. A returned non-success produces an
outer PARTIAL containing the retained map; the node's original outcome remains
intact. Raised errors use safe WorkflowError summaries with original causes.
Actual cancellation propagates and leaves progress accessible via executor.results.
Nested payloads are still shared, and handlers own resource cleanup.

**EXERCISE (optional, not a required production change):** make the first handler
return RETRY and predict the calls/result map. Then compare returning CANCELLED
with cancelling a task blocked inside a handler. Retain a snapshot before a
second run and confirm it does not change.

**INTERVIEW QUESTIONS:** Why is a binding sequence preferable for detecting
duplicates? Why does outer PARTIAL preserve outcomes that outer FAILED cannot?
Why must a rejected concurrent call leave the first run's store untouched?

## Run a workflow through managed Runtime lifecycle

**WHY:** a component must not be torn down during a workflow admitted through its
Runtime. **WHAT:** use run_workflow for the same deterministic DAG example above.
**HOW:** initialize and start managed lifecycle, await the run, then stop.

**IMPLEMENT:** examples.sequential_workflow now follows this pattern using its
existing graph and executor:

```python
from agentos.runtime import Runtime

runtime = Runtime.from_settings()
await runtime.initialize_async()
await runtime.start_async()
try:
    outcome = await runtime.run_workflow(executor, 7)
finally:
    await runtime.stop_async()
```

Run `uv run --locked --no-sync python -m examples.sequential_workflow`; the
reference value remains 14. The example awaits execution before shutdown, so a
handler error or cancellation propagates through cleanup before stop is called.

If your application creates a task for the run, it owns that task. stop_async
rejects while it is active: await it to completion, or explicitly cancel and await
it if your application policy calls for cancellation, then retry shutdown.
Runtime does not create background tasks, drain work, or cancel handlers for you.

**TEST:** event-barrier regressions cover both shutdown/workflow race orderings,
nested/overlapping admission, independent Runtimes, retained report identity and
snapshots, executor admission errors, exception causes and actual cancellation.
**EXPLAIN THE CODE:** the active flag is set without awaiting, executor.run is
awaited directly without a lifecycle lock, and finally clears admission.
Shutdown checks the same flag under its lifecycle lock before teardown.

**EXERCISE (optional):** suspend a handler on an asyncio.Event, call stop_async
and observe rejection, then release and await the workflow and retry stop.
**INTERVIEW QUESTIONS:** Why check the lifecycle lock as well as STARTED?
Why would sharing ComponentManager between Runtimes defeat this guard?
Why must a cancelled task be awaited before its resources are torn down?

The guarantee covers one Runtime on one event loop. Direct manager calls,
shared managers and standalone executor/agent execution bypass it. Payload
immutability remains shallow, cancellation cooperative, and cleanup handler-owned.
