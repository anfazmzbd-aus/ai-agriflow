# AgentOS API

`agentos.core.ExecutionResult[T]` is the typed outcome contract. Use its
`success`, `failure`, `timeout`, `partial`, `retry`, or `cancelled` factories.
Successful and partial results carry a value; `has_value` distinguishes an
explicit `None` value from no value. Failed and timeout results require a
non-empty error message. Retry and cancellation messages are optional. Metadata
is copied on construction and returned as a read-only mapping.

AgentOS framework exceptions are rooted at `AgentOSError` and exported from
`agentos.base`. `ComponentError` groups operational component failures;
`ConfigurationError` represents invalid configuration. Domain errors include
`AgentOSRuntimeError`, `WorkflowError`, `AgentError`, `ToolError`, `ModelError`,
`AgentOSMemoryError`, and `RegistryError`. `RegistrationError` remains available
and derives from `RegistryError`; `ServiceError` reports service container
registration or resolution failures. When translating a lower-level exception, use
`raise DomainError("safe summary") from exc` to retain the original cause. Keep
credentials and secret values out of exception messages.

`agentos.base.Component` remains the abstract component interface.
`agentos.base.BaseComponent` is a concrete implementation that accepts a stable
name at construction. Names must be strings containing at least one non-whitespace
character; valid names are preserved as supplied and exposed through a read-only
property. Lifecycle operations are defined separately from component identity.

### Lifecycle components

`agentos.base.LifecycleComponent` is an opt-in asynchronous base for components that
own resources. Implement `_initialize()`, `_start()`, and `_stop()` hooks; call
`initialize()`, `start()`, and `stop()` to run them. Hooks must not recursively call
the public lifecycle methods. Per-instance synchronization serializes concurrent
calls. Repeated initialization while initialized, start while started, and stop
while stopped are no-ops. Stopping a new component moves it directly to stopped
without invoking cleanup. A failed or cancelled hook leaves the component failed;
`stop()` can then retry cleanup. The original exception or cancellation propagates.

| Current state | Call | Resulting state | Hook |
| --- | --- | --- | --- |
| `NEW` | `initialize()` | `INITIALIZED` | `_initialize()` |
| `INITIALIZED` | `initialize()` | `INITIALIZED` | none |
| `INITIALIZED` | `start()` | `STARTED` | `_start()` |
| `STARTED` | `start()` | `STARTED` | none |
| `NEW` | `stop()` | `STOPPED` | none |
| `INITIALIZED` or `STARTED` | `stop()` | `STOPPED` | `_stop()` |
| `STOPPED` | `stop()` | `STOPPED` | none |
| `FAILED` | `stop()` | `STOPPED` on success; otherwise `FAILED` | `_stop()` |

Starting before initialization, initializing a started component, or initializing/
starting a stopped or failed component raises `AgentOSRuntimeError` without changing
state. An ordinary hook exception or cancellation marks the component failed and is
re-raised unchanged. `KeyboardInterrupt` and `SystemExit` propagate without being
caught or changing lifecycle state. Cancellation while waiting for the transition
lock has no state effect. After a hook returns, the state update runs synchronously
with no intervening await, so cancellation cannot arrive in the gap between hook
success and that transition being recorded.

The states are `NEW`, `INITIALIZED`, `STARTED`, `STOPPED`, and `FAILED`. Stopped is
terminal: components cannot restart. Lifecycle hooks return `None`; operation
outcomes continue to use `ExecutionResult[T]` where appropriate. This contract does
not discover components or coordinate startup order; those concerns belong to a
future component manager/runtime integration.

### Base agents

`agentos.agents.BaseAgent[InputT, OutputT]` is an abstract, lifecycle-aware base for
typed asynchronous agents. Implement `_execute(input)` and override lifecycle hooks
only when resource setup or cleanup is needed. The default hooks are no-ops. Call
`initialize()` and `start()` before `run(input)`; calls to `run()` outside `STARTED`
raise `AgentOSRuntimeError` before execution. Successful calls return the raw typed
output. `AgentError` propagates unchanged; unexpected ordinary exceptions become a
safe `AgentError` chained from the original. Cancellation, `TimeoutError`,
`KeyboardInterrupt`, and `SystemExit` propagate unchanged. No retry or timeout is
performed internally.

The started-state check is an admission check only. A concurrent `stop()` may finish
while `_execute()` is still awaiting; the in-flight call may then complete while the
agent state is `STOPPED`. Execution does not mutate lifecycle state. A
`BaseAgent[AgentContext, AgentResult]` specialization is structurally compatible with
the existing `Agent` protocol; `EchoAgent` and the protocol itself are unchanged.

### Event system

`agentos.events.EventBus` dispatches `Event` objects in-process. Subscribe with a
nonblank exact event type or the global wildcard `"*"`; the value is preserved as
provided. Other event-type strings containing `*` are literal names, not patterns.
Each call to `subscribe()` is a separate registration, including repeated
registrations of the same handler. `unsubscribe()` removes the first equal
registration and returns whether it found one. `subscriber_count()` counts exact
registrations only (or global registrations when queried with `"*"`).

Each `publish()` snapshots its handlers before callbacks begin, runs exact handlers
in registration order, then global wildcard handlers in registration order, and
awaits each sequentially. Subscription changes during dispatch affect future
publishes only. A handler exception propagates unchanged and stops later handlers;
cancellation also propagates and stops dispatch. Publishing with no subscribers is
a successful no-op. Concurrent publishes are independent and may interleave; the
bus does not provide cross-publication ordering or thread-safety guarantees.

`Event.type` must be a nonblank string and valid values are preserved exactly. Event
instances and payloads remain mutable for compatibility. Payloads are in-process
Python data, are passed to handlers without serialization or deep copying, and may
be mutated by handlers. External broker serialization, persistence, retries, and
background delivery are outside this API.

::: agentos

::: agentos.core

::: agentos.runtime

### Runtime lifecycle

`agentos.runtime.Runtime` keeps its existing constructor order—settings, EventBus,
Registry, telemetry—and `Runtime.from_settings()` factory. Four-argument manual
construction remains supported. Runtime creates a `ServiceContainer` and
`ComponentManager` by default and binds the core objects by their concrete Python
class keys. Runtime fields and resolved core services refer to the same objects.
Python generic specializations such as `Registry[object]` are not separate runtime
class keys; a Runtime owns one `Registry`, registered under the `Registry` class key.

Runtime preflights all six core keys before registering any of them. A key already
present in a supplied container raises `ServiceError` because the container cannot
inspect a factory's eventual identity without constructing it. Unrelated user service
registrations are preserved. Runtime does not resolve arbitrary application services;
use `runtime.services` explicitly. It does not initialize or dispose services.

The synchronous `Runtime.start()` remains the legacy logging-configuration and
`runtime.started` telemetry operation. It does not start managed components. Once any
managed lifecycle call is requested, the legacy method raises `AgentOSRuntimeError`
instead of emitting a misleading readiness event. Managed lifecycle uses
`initialize_async()`, `start_async()`, and `stop_async()`; these delegate to
`ComponentManager` and expose its read-only state through `runtime.state`.
`start_async()` requires prior initialization and never invokes the synchronous
method. No async work is run through an implicit event loop.

The Runtime lock serializes its managed methods and rejects same-task recursive calls.
Cancellation while waiting for the Runtime lock does not change manager state, though
the legacy/managed mixing boundary becomes closed once the managed request begins.
Ordinary telemetry errors are suppressed for managed transitions and cannot replace
lifecycle results. Telemetry control-flow exceptions propagate after the state change.
Failure telemetry is attempted only once the manager is `FAILED`. Runtime does not
publish lifecycle events through EventBus, retry telemetry, or drain in-flight agent
execution. Do not replace the public `services` or `component_manager` fields after
construction: doing so breaks the identity between Runtime fields and their core
container bindings.

::: agentos.events

::: agentos.registry

::: agentos.manager

::: agentos.tools

::: agentos.agents

::: agentos.memory

::: agentos.models

### Workflow graph declarations

`agentos.workflows.WorkflowGraph` validates an ordered, nonempty sequence of
`WorkflowNodeSpec` declarations. A `NodeId` is a string-backed static type.
Use plain, nonblank strings for IDs. Each ID is local to its graph, case-sensitive,
and preserved exactly. Each declaration has a `depends_on` tuple of direct
predecessors, which may be declared later in the sequence.

```python
from agentos.workflows import NodeId, WorkflowGraph, WorkflowNodeSpec

weather = NodeId("weather")
soil = NodeId("soil")
advisory = NodeId("advisory")
graph = WorkflowGraph(
    nodes=(
        WorkflowNodeSpec(advisory, depends_on=(weather, soil)),
        WorkflowNodeSpec(weather),
        WorkflowNodeSpec(soil),
    ),
)

assert graph.topological_order() == (weather, soil, advisory)
assert graph.nodes[advisory].depends_on == (weather, soil)
```

`graph.nodes` is a read-only mapping in declaration order. Unknown IDs raise
`KeyError` through mapping lookup. `graph.edges` is a tuple of `WorkflowEdge`
values, identified by their `(prerequisite, dependent)` pair. Edges are listed
in dependent declaration order, then in that node's dependency declaration
order. Nodes, dependencies, edges, and the precomputed order are immutable.
Build a new graph to change its topology.

When several nodes are ready, `topological_order()` places the earliest
declared node next, including newly ready nodes. Singleton, disconnected,
and isolated nodes are supported. Construction checks input shape, graph
emptiness, node declarations and IDs in node order, then dependency shape,
IDs, duplicates, and self-references in declaration order. Missing references
are checked next, then cycles. Invalid topology raises
`agentos.base.WorkflowGraphError`, a subclass of `WorkflowError`.
Diagnostics use declaration positions where applicable and omit raw IDs.
Cycle errors report the presence of a cycle. They provide no cycle path.

The graph models synchronous, in-process topology. Use `SimpleWorkflow`,
`WorkflowContext`, and `WorkflowStep` for the existing linear runner.

::: agentos.workflows

::: agentos.adapters

::: agentos.telemetry

### Service container

`agentos.container.ServiceContainer` maps Python class objects to explicit service
instances or synchronous factories. Class keys may be concrete classes, abstract
classes, or Protocols. Factories receive the container and may call `resolve()` for
their dependencies. Registration is unique; duplicate keys raise `ServiceError`.
Instances preserve identity. Factories default to lazy singleton lifetime and may
select `lifetime="transient"` to construct a new result for each resolution.
Singleton results are cached only after successful, non-`None` construction.

`resolve(ServiceType)` returns the generic type declared by that key. This is a
static typing contract; the container does not use runtime `isinstance()` checks.
Because MyPy models `type[T]` as a constructible class, Protocol and abstract-class
tokens need an explicitly typed `type[Interface]` cast/alias at the registration
site; resolving through that typed token retains the interface result type.
Missing registrations and direct or indirect circular dependencies raise
`ServiceError`. Factory exceptions propagate unchanged, and failed singleton
construction can be retried. `None` instances and `None` factory results are
rejected. There is no replacement API.

Registration and resolution are synchronous and serialized by a per-container
reentrant lock. This ensures a singleton factory is successfully run at most once,
including concurrent resolution. Factories should be short-running and must not
synchronously wait for another thread that needs the same container. Async factories
and awaitable factory results are unsupported. The container does not initialize,
stop, or dispose services; it is independent of `Registry`, `Runtime`, and `EventBus`.

### Component manager

`agentos.manager.ComponentManager` coordinates explicitly registered
`LifecycleComponent` instances. Register a component with
`register(component, depends_on=("dependency-name",))`; forward references are
allowed, but missing dependencies, duplicate dependency declarations, self-dependency,
and cycles raise `ConfigurationError` before any lifecycle hook runs. `get(name)`
uses the existing `Registry` lookup and duplicate-name behavior (`RegistrationError`),
and `names()` returns registration order. Registering the same object twice is rejected even under another
name. There is no replacement or unregistration API.

Dependencies describe lifecycle ordering only and are independent of
`ServiceContainer` construction dependencies. A stable topological order uses
registration order to break ties. The manager initializes all components before it
starts any, then stops in reverse topological order. Registration closes after
preflight and before initialization hooks begin. Before hooks run, the manager requires all registered
components to be `NEW`; preflight failures do not run hooks or mark the manager
failed. Registration remains closed throughout lifecycle operations and after
initialization starts. `initialize()`, `start()`, and `stop()` are idempotent after their respective
successful transitions. `start()` does not implicitly initialize components, and
`STOPPED` is terminal.

| Manager state | Call | Result |
| --- | --- | --- |
| `NEW` | `initialize()` | `INITIALIZED` after all hooks succeed; hook failure/cancellation gives `FAILED` |
| `NEW` | `start()` | Invalid; remains `NEW` |
| `NEW` | `stop()` | `STOPPED`; new components' stop hooks are not invoked by the component contract |
| `INITIALIZED` | `initialize()` | Idempotent no-op |
| `INITIALIZED` | `start()` | `STARTED` after all hooks succeed; hook failure/cancellation gives `FAILED` |
| `INITIALIZED` or `STARTED` | `stop()` | `STOPPED` after cleanup; cleanup failure gives `FAILED` |
| `STARTED` | `start()` | Idempotent no-op |
| `FAILED` | `stop()` | `STOPPED` after successful retry; otherwise remains `FAILED` |
| `FAILED` or `STOPPED` | `initialize()` or `start()` | Invalid; state unchanged |
| `STOPPED` | `stop()` | Idempotent no-op |

Dependency-graph and component-state preflight errors occur before hooks and leave the
manager `NEW`, allowing registration/configuration to be corrected before retry.

Ordinary hook failures propagate unchanged when rollback succeeds. If rollback also
fails, the original failure and rollback failures are retained in an `ExceptionGroup`.
Shutdown attempts all components even after ordinary cleanup failures; failures are
grouped, the manager remains `FAILED`, and a later `stop()` retries every component
that is not stopped. Cancellation, `KeyboardInterrupt`, and `SystemExit` are
propagated without wrapping after best-effort cleanup; a second interruption can
interrupt cleanup, so call `stop()` again to retry. An asyncio lock serializes
manager lifecycle operations. Same-task recursive lifecycle calls fail with
`AgentOSRuntimeError`; cancellation while waiting for that lock has no state effect.
Because `LifecycleComponent.stop()` from `NEW` deliberately skips its hook, a
process-control exception raised during that component's initialization cannot
invoke its cleanup hook through the public lifecycle contract; the manager still
attempts `stop()` and records the manager as `FAILED`.
The manager does not create services, emit events, manage Runtime, or drain in-flight
agent executions. As with `BaseAgent`, an execution already admitted may finish after
manager shutdown completes.

### DAG node contexts and retained results (Task 3.2)

The linear `WorkflowContext` and `WorkflowStepHandler` remain unchanged.
DAG handlers use a separate `WorkflowNodeContext[InputT]`, created by a
`WorkflowRunState[InputT]`. The run owner retains outcomes; a node view exposes
only its direct prerequisites. These types do not schedule or execute nodes.

Public exports from `agentos.workflows`:

```python
WorkflowNodeContext(node_id, input_data, dependency_results)
WorkflowRunState(graph, input_data=input_data)
# WorkflowNodeHandler[InputT, OutputT] is:
# Callable[[WorkflowNodeContext[InputT]], Awaitable[ExecutionResult[OutputT]]]
```

- `context.node_id: NodeId` and `context.input_data: InputT` are frozen fields.
- `context.dependency_results: Mapping[NodeId, ExecutionResult[object]]` is a
  copied, read-only snapshot. `dependency_result(node_id)` returns one visible
  outcome with safe diagnostics when it is unavailable.
- `run.record_result(node_id, result: ExecutionResult[OutputT]) -> None` records
  an existing graph node exactly once, retaining the original result identity.
- `run.result_for(node_id) -> ExecutionResult[object]` returns a retained outcome.
- `run.results` returns a fresh read-only snapshot, independent of later records.
- `run.context_for(node_id) -> WorkflowNodeContext[InputT]` requires every direct
  dependency result and preserves the declared dependency order. It excludes
  transitive and unrelated results. Root contexts have an empty dependency map.

A direct context constructor validates IDs and mapping shape, but has no graph
against which to check dependency membership. Use `context_for` for graph-scoped
views. All reference-taking helpers reject malformed or unknown IDs without
including those values in diagnostic messages. Invalid context/run operations use
the existing `WorkflowError` hierarchy. Duplicate records do not replace outcomes.

Every run owns a separate result dictionary and can share the same immutable graph.
The owner is intended for a single coordinator, without concurrent writers. Contexts
have no supported route to mutate the owner's store. Mapping copies are shallow:
input objects, result values, and nested metadata remain shared references. Treat
them as immutable while in use; provide separate mutable inputs for separate runs
when needed. No deep copy, persistence, eviction, or retry replacement is provided.

Dependency outputs are heterogeneous, so lookups expose `object`; narrow the value
explicitly. No typed lookup claims that a string ID proves the output type. Internal
storage uses one documented erasure cast because `ExecutionResult` is invariant.

| Status | Retained contract |
| --- | --- |
| SUCCESS | `has_value=True`, including a legitimate `None`; no error |
| FAILED | No value; required nonblank error |
| PARTIAL | Value present; optional error |
| RETRY | No value; optional error; no automatic retry |
| TIMEOUT | No value; required error; no timeout machinery |
| CANCELLED | No value; optional error |

Context construction checks result availability, not dependency success. In
particular, it does not use `is_terminal` to decide execution readiness.
Handlers must explicitly return an `ExecutionResult`. A raised exception stays an
exception: these contracts add no invocation wrapper, normalization, retry, or
cancellation interception. Actual cancellation and process-control exceptions
propagate. Scheduling and failure policy belong to separately authorized Task 3.3.

Default representations of the new context and owner omit IDs, inputs, outcomes,
and metadata. Helpers use fixed diagnostic messages. Payloads, caller-supplied
error strings, raw mapping `KeyError` messages, and full exception tracebacks can
still expose sensitive data if callers print them. These contracts perform no
automatic logging or serialization and do not provide a security sandbox.

### Sequential DAG executor (Task 3.3)

`WorkflowNodeBinding[InputT](node_id, handler)` binds a precise
`WorkflowNodeHandler[InputT, OutputT]` to one node. The binding is immutable.
Its generic constructor accepts heterogeneous output types without caller casts;
only private storage erases them to `object`.

`SequentialWorkflowExecutor[InputT](graph, bindings)` accepts an ordered sequence
of bindings, snapshots it, and validates the complete set before invoking anything.
It rejects malformed collections/bindings, duplicate IDs, extra bindings, and
missing bindings with safe `WorkflowError` diagnostics. The same callable may
serve different node IDs. IDs retain the graph's exact case-sensitive semantics.
Preflight checks callability without executing user code; static typing verifies
the async/result contract, and invocation validates actual awaitability and output.

```python
async def run(
    self, input_data: InputT
) -> ExecutionResult[Mapping[NodeId, ExecutionResult[object]]]: ...


@property
def results(self) -> Mapping[NodeId, ExecutionResult[object]]: ...
```

Each admitted run creates a fresh `WorkflowRunState`. Nodes execute one at a time
in `graph.topological_order()`, irrespective of binding order. Global fail-fast
ensures all previously recorded dependencies have SUCCESS status before another
node starts. Direct-dependency visibility remains governed by `context_for`.

| Node event | Executor policy |
| --- | --- |
| Returned SUCCESS | Retain the original result and continue; successful None is valid |
| Returned FAILED, TIMEOUT, CANCELLED, PARTIAL or RETRY | Retain the original result; stop all later nodes, including independent nodes |
| Raised ordinary Exception | Record a synthetic safe FAILED; raise WorkflowError from the original cause |
| Raised TimeoutError | Record a synthetic safe TIMEOUT; raise chained WorkflowError |
| Raised asyncio.CancelledError | Record synthetic safe CANCELLED for the attempted node; re-raise unchanged |
| KeyboardInterrupt, SystemExit or other BaseException | Propagate unchanged; preserve only already recorded outcomes |
| Invalid awaitable or returned value | Record safe FAILED; raise safe WorkflowError; preserve the cause when one was raised |

All nodes succeeding returns an outer SUCCESS containing the immutable result map.
A returned non-success produces outer PARTIAL with that map and a fixed safe error
summary. The stopping node's original status, value, error and identity remain
inside the map. Outer PARTIAL means incomplete workflow success with outcomes
available, including when the first node failed. It does not trigger more work.
No new status hierarchy is introduced, and `is_terminal` never controls iteration.
Unattempted nodes are absent; there is no invented SKIPPED outcome.

Actual cancellation raises rather than returning a normal report. Returned
CANCELLED produces a normal PARTIAL report and does not cancel the calling task.
Raised ordinary errors preserve their original object/traceback through
`__cause__`; their public summaries omit raw exception text and node IDs.
No handler wrapper, status behavior, or direct exception propagation contract
outside this new executor is changed.

`executor.results` exposes a read-only snapshot of active progress or the final
retained outcomes. Snapshot copies occur on reads and finalization, not after
every node. A second active or reentrant run is rejected without resetting the
first. Admission is released in a synchronous finally block on every exit.
Cancellation before coroutine admission leaves the previous snapshot unchanged.
The next admitted run starts empty; old snapshots remain valid. Separate executor
instances may run concurrently, but one instance is not a thread-safe or
multi-event-loop writer API. Handlers and mutable payloads may still be shared.

Handlers own cleanup using their own finally/context managers. The executor adds
no rollback, lifecycle hooks, shielding, cancellation suppression, retries,
timeouts, workers, or Runtime integration. Cancellation is cooperative; blocking
handler code cannot be preempted. A second cancellation may interrupt handler
cleanup according to normal asyncio behavior.

Representations of bindings/executors omit IDs, callables, inputs and outcomes.
Inputs, values and nested metadata remain shallow immutable-by-convention
references. Explicitly printing raw mappings, caller error strings or complete
exception chains can still disclose sensitive data. These contracts are not a
Python security sandbox.

### Runtime-managed workflow execution (Task 3.4)

`Runtime.run_workflow` admits one supplied executor after managed initialization
and startup. Legacy synchronous `start()` does not establish readiness.

```python
async def run_workflow[InputT](
    self,
    executor: SequentialWorkflowExecutor[InputT],
    input_data: InputT,
) -> ExecutionResult[Mapping[NodeId, ExecutionResult[object]]]: ...
```

Admission requires `state is LifecycleState.STARTED`, an idle Runtime lifecycle
lock, and no active managed workflow on that Runtime. Checks and admission happen
without an intervening await on one event loop. Rejected admission raises a fixed
`AgentOSRuntimeError` without invoking the executor or changing its snapshots.
Overlapping and nested calls are rejected, even with different executors.
Independent Runtimes with separate managers and executors may run concurrently.

Runtime directly awaits `executor.run(input_data)` in the caller's task without
holding its lifecycle lock. It returns the exact SUCCESS or PARTIAL report;
node result identities, successful None, all statuses and snapshots remain owned
by the executor. WorkflowError and its original cause, actual CancelledError,
and process-control exceptions propagate unchanged. Returned CANCELLED remains
the executor's normal PARTIAL report. Workflow outcomes do not change lifecycle
state or emit telemetry. Admission is cleared in finally on every exit, including
executor admission errors, so later execution and shutdown can proceed.

`stop_async()` checks for an active managed workflow inside its existing lifecycle
lock, before ComponentManager teardown or lifecycle telemetry. It rejects active
work with a fixed AgentOSRuntimeError rather than waiting, cancelling, or draining.
The caller must settle the workflow, including handler cleanup, then retry stop.
If shutdown wins admission, its held lifecycle lock rejects new workflow calls
even while aggregate state still reads STARTED.

The shutdown guarantee applies only to calls through the same Runtime on one
event loop. Direct ComponentManager lifecycle calls, sharing a manager across
Runtimes, and standalone executor/agent execution bypass this guard. Public core
service/manager identity constraints remain in force. This method performs no
registry lookup, service resolution, registration, background scheduling,
automatic retry/timeout, rollback, or workflow telemetry.
