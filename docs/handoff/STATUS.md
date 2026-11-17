# Handoff status

- Project: AgentOS framework + AgriFlow application
- Phase: Sprint 2 administrative closure — Task 2.13 post-release handoff documentation
- Baseline task: **2.3.1 ExecutionStatus** (reconstructed implementation)
- Completed task: **2.3.2 ExecutionResult[T]** — committed as `9c79638`; user-verified
- Completed task: **2.3.3 Core Exception Hierarchy** — committed; user-verified
- Completed task: **2.4 BaseComponent** — committed as `7338f51`; user-verified
- Completed task: **2.5 Lifecycle Contracts** — user-verified and merged into `main` as `57f9383b83c65062fd04f889dcb141af5e207c66`
- Pull request: **#1** (`feat/2.5-lifecycle` → `main`) — merged; GitHub Actions CI passed before merge
- Completed task: **2.6 BaseAgent** — verified and merged into `main` as `c34c19b5fe592daa3dd26c1de1bf269c38360bee`
- Pull request: **#2** (`feat/2.6-base-agent` → `main`) — merged; standard merge commit
- Completed task: **2.7 Event System** — committed as `45482d442243a1a02c4e09c7a93bb0443c466471` and pushed to `origin/feat/2.7-event-system`
- Pull request: **#3** (`feat/2.7-event-system` → `main`) — merged into `main` as `2ad392fc3f0ccc9355ed1d99db05c81d00c50ea1`
- Completed task: **2.8 Service Container** — committed as `168be89f284f6800493d27d13cad574b2bb87d85` and pushed to `origin/feat/2.8-service-container`
- Pull request: **#4** (`feat/2.8-service-container` → `main`) — merged in `779dae278a9eb6015bb1791c0090d08a201eef93`
- Pull request: **#5** (`feat/2.9-component-manager` → `main`) — merged in `26313e5ea6229883d378f0b2be3ade1bdfe256f6`
- Completed task: **2.10 Runtime Integration and Orchestration** — implementation commit `2b990a2d5d8ec4f7ee86af20f83b34156b041d34`, documentation commit `323def301b80b5f02105ab0c866391360a62f8e4`, merged as `d6afa8a3828ba4d8736d6df0e799a9249f83d559`
- Pull request: **#6** (`feat/2.10-runtime` → `main`) — merged; GitHub Actions CI passed before merge
- Completed task: **2.11 Integration Testing and System Validation** — committed as `20129d0c42c7eddaf17c99426cc2f94c21f3854c`, pushed, and merged into `main` as `8daf6db6e7685ddc2ac2eaa278525f948d075705`
- Pull request: **#7** (`feat/2.11-integration-tests` → `main`) — merged; GitHub Actions CI passed before merge
- Source fidelity: original user's local Git repository was not available; reconcile before merging.

## Task 2.3.2 implementation

Added generic `ExecutionResult[T]`, status-specific factories/invariants, explicit
`has_value` semantics for legitimate `None`, copied read-only metadata, core exports,
focused tests, and API/tutorial documentation. `ExecutionStatus` is exported from
`agentos.core`. Necessary baseline fixes add missing public/test docstrings and format
three pre-existing files for Ruff compliance. `pyproject.toml` and `uv.lock` are
unchanged. Existing `AGENTS.md` and `README.md` edits predate this task and are excluded
from its proposed commit.

## USER-EXECUTED VERIFICATION — 2026-10-23

The following evidence was supplied by the user from interactive Windows PowerShell,
Python 3.14.0 and the uv-managed environment. Codex did not execute these successful
checks. The user confirms the verified source was the current working tree revision.

| Check | User-reported result |
| --- | --- |
| Minimal asyncio via uv and directly through `.venv` | PASS |
| Minimal asyncio on Python 3.12 and Python 3.14 | PASS |
| Previously hanging E2E test | 1 passed in 0.11 seconds |
| Full pytest suite | 45 passed; coverage 98.21% (threshold 80%) |
| Ruff lint | PASS |
| Ruff formatting | PASS; 71 files checked |
| MyPy | PASS; 33 source files checked |
| Offline package build | PASS |
| Pytest cache | Nonfatal WinError 183 warning |

## Codex GUI execution discrepancy

The Codex GUI environment timed out while running `asyncio.run(asyncio.sleep(0))`
under Python 3.14.0, 3.12.10, and 3.12.12, both outside uv and under the default
Windows Proactor policy. Selector-policy probes also timed out on Python 3.14.0 and
3.12.10. The isolated E2E and full suite similarly timed out in the GUI environment.
The user's successful interactive PowerShell results demonstrate an execution-
environment discrepancy. Its root cause is unconfirmed. No Python version, event-loop
policy, test logic, or coverage threshold was changed to work around it.

Codex recovered the locked dev extra with `uv sync --locked --extra dev --offline`
after a networked attempt failed resolving `files.pythonhosted.org`. Codex's Ruff,
format, MyPy, focused tests, and elevated offline build passed. GUI full-suite evidence
is superseded by the explicitly attributed user-executed full-suite results above.

## Proposed Task 2.3.2 commit scope

Include the implementation, exports, tests, docs, this status record, and baseline
corrections:

- `src/agentos/core/execution_result.py`
- `tests/unit/core/test_execution_result.py`
- `src/agentos/core/__init__.py`
- `docs/api/agentos.md`
- `docs/tutorials/getting-started.md`
- `docs/handoff/STATUS.md`
- `src/agentos/__init__.py`
- `src/agentos/core/execution_status.py`
- `tests/unit/core/test_execution_status.py`
- `tests/unit/tools/test_tool.py`
- `tests/unit/workflows/test_workflow.py`

Exclude pre-existing `AGENTS.md` and `README.md` edits. No commit has been created.
## Task 2.3.3 implementation

Reuses the existing `AgentOSError` root and `ComponentError` base. Adds runtime,
agent, tool, model, memory, configuration, and registry domain exception types while
preserving `WorkflowError` and keeping `RegistrationError` as a subtype of
`RegistryError` and `ComponentError`. Added hierarchy and chaining tests and API
documentation. No exception carries structured codes or arbitrary context; retry
policy remains with callers. Error messages should be safe summaries and translations
should use exception chaining.

### Verification

- **USER-EXECUTED VERIFICATION (Windows PowerShell):** `uv run pytest -q` — 49
  passed in 0.44 seconds; total coverage 98.24%, above the configured 80% threshold.
  Ruff lint, Ruff formatting, MyPy, and offline package build also passed in the
  user's environment. The user reported no reproduced asyncio hang there.
- **CODEX-EXECUTED VERIFICATION:** The focused exception suite passed (4 tests) with
  `--no-cov`; Ruff lint, Ruff format check, MyPy, offline sync, and elevated offline
  build passed. The full pytest run timed out in Codex GUI, with no full-suite result.
  This GUI discrepancy does not reproduce in the user's PowerShell environment; its
  root cause remains unconfirmed.
- `uv sync --locked --extra dev --offline`: PASS; 83 locked packages audited.
- `uv run pytest tests\\unit\\base\\test_exceptions.py --no-cov -q`: PASS; 4 passed.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 72 files formatted.
- `uv run mypy src`: PASS; no issues in 33 source files.
- `uv build --offline`: PASS in approved elevated run; source distribution and wheel built.
- User-executed `uv run pytest -q` verifies the current Task 2.3.3 source: 49 passed,
  0.44 seconds, 98.24% coverage. Codex GUI's full-suite run timed out as described
  above; no code/config workaround was applied.

Focused tests with repository coverage enabled ran 4 tests but exited at 35.43%,
because the configured 80% threshold measures total project coverage. The focused
suite passed with `--no-cov`; the threshold was not changed. Await user review and
explicit commit approval. Task 2.4 has not started.

## Task 2.4 implementation (verified; awaiting commit approval)

The approved scope preserves the abstract `Component` interface and adds concrete
`BaseComponent(Component)` with validated, exact-preservation, read-only names. No
lifecycle, event, registry, or runtime operations are included. Implementation and
tests were added; existing `Component` subclasses remain valid.

### Codex-executed verification

- `uv sync --locked --extra dev`: PASS; 83 packages resolved/audited.
- `uv run pytest tests/unit/base/test_component.py -q --no-cov`: PASS; 12 passed
  (initial run 0.16s; rerun after lint fixes 0.12s).
- `uv run pytest -q`: stalled in Codex GUI for over 60 seconds and was interrupted;
  no full-suite count or coverage is available from this environment.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 72 files checked.
- `uv run mypy src`: PASS; no issues in 33 source files.
- `uv build --offline`: PASS in approved elevated run; source distribution and wheel built.

### USER-EXECUTED VERIFICATION (Windows PowerShell)

The user ran the complete suite against the current Task 2.4 working tree using
Python 3.14.0 and the uv-managed environment:

- `uv run pytest -q`: PASS; 60 passed in 0.50 seconds.
- Repository coverage: 98.31%, above the configured 80% threshold.
- `BaseComponent` module coverage: 100%.
- Ruff lint, Ruff formatting, MyPy, locked uv sync, and offline package build: PASS.
- Codex focused `test_component.py`: 12 passed.

The Codex GUI full-suite timeout remains an unresolved execution-environment
discrepancy; the user did not reproduce it in PowerShell. No asyncio, Python-version,
test, or coverage workaround was made. Task 2.5 work is recorded below.

## Task 2.5 implementation (committed, pushed, user-verified, and merged)

Branch setup: fetched `origin`, created local `feat/2.5-lifecycle` tracking
`origin/feat/2.5-lifecycle`, and verified Task 2.4 commit `7338f51c2137e6e73ae2a3b9c90fbacb42ac490a`
is an ancestor. The branch begins at `ed55b65` (`frontend : landing page updates`);
the intervening frontend commits did not modify lifecycle files. Existing edits to
`.gitignore`, `AGENTS.md`, `README.md`, and `pyproject.toml` were preserved.

Implemented an opt-in `LifecycleComponent(BaseComponent)` and `LifecycleState` with
serialized async initialize/start/stop methods, idempotent repeated calls, explicit
invalid-transition errors, failure/cancellation propagation, cleanup retry from
FAILED, and same-task reentrancy protection. `Component` and `BaseComponent` remain
unchanged. Lifecycle methods return `None`; no manager or runtime orchestration was
added. Documentation and deterministic tests are included.

### Codex-executed verification

- `uv sync --locked --extra dev`: PASS; 83 packages resolved/audited.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 76 files formatted.
- `uv run mypy src`: PASS; no issues in 34 source files.
- `uv run pytest tests/unit/base/test_lifecycle.py -q --no-cov`: GUI execution
  stalled before reporting the first test; interrupted. The verbose run collected
  17 cases before the final additional case was added, then stalled at the first.
- `uv run pytest -q`: GUI execution stalled with no output for 25 seconds; interrupted.
- `uv build --offline`: attempted with approved elevated access; did not complete
  within the GUI call and was interrupted.

The async test/build stalls are unresolved Codex GUI execution-environment
discrepancies. No event-loop, Python, test, dependency, or coverage configuration
workaround was introduced.

### USER-EXECUTED VERIFICATION (Windows PowerShell)

The user ran the full verification suite on branch `feat/2.5-lifecycle`:

- `uv sync --locked --extra dev`: PASS; 83 packages.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 76 files.
- `uv run mypy src`: PASS; 34 source files.
- `uv build --offline`: PASS; source distribution and wheel built.
- `uv run pytest tests/unit/base/test_lifecycle.py -q --no-cov`: PASS; 18 passed
  in 0.16 seconds.
- `uv run pytest -q`: PASS; 78 passed in 0.47 seconds.
- Repository coverage: 98.20%, above the 80% threshold; lifecycle module coverage
  approximately 98%.

Codex GUI execution of focused/full async tests and offline build did not complete;
those outcomes remain an unresolved environment discrepancy and are recorded
separately above. User-executed results supersede the GUI timeout for this source
revision. Task 2.5 was committed as
`980dbc3f63bfd518d4c10e56d28b0347f8b52b6a` and pushed to
`origin/feat/2.5-lifecycle`. PR #1 targeted `main` and has been merged. GitHub
merged PR #1 into `main` as
`57f9383b83c65062fd04f889dcb141af5e207c66`; GitHub Actions CI passed before merge.
The local `main` branch has been fast-forwarded to `origin/main` at that merge
commit. Task 2.4 remains committed as `7338f51`. Task 2.6 implementation is recorded
below; Task 2.7 requires separate authorization. The Codex GUI async-test/build timeout remains an
unresolved execution-environment discrepancy; user-executed Windows PowerShell
results above are recorded separately and were successful.

### PR #1 exception-handling review correction

Changed `_invoke_hook()` to handle `asyncio.CancelledError` and ordinary
`Exception` explicitly. Both mark the lifecycle state `FAILED` and propagate the
original exception with its traceback. `KeyboardInterrupt` and `SystemExit` now
propagate without being caught or changing lifecycle state. Regression tests cover
exception identity, traceback preservation, and unchanged state for process-control
exceptions. API documentation describes this behavior. No lifecycle transition,
public API, dependency, or unrelated working-tree files were changed.

**Codex-executed verification for this correction:**

- `uv sync --locked --extra dev`: PASS; 83 packages audited.
- `uv run pytest tests/unit/base/test_lifecycle.py -q --no-cov`: PASS; 20 passed
  in 0.16 seconds.
- `uv run pytest -q`: PASS; 80 passed in 0.53 seconds; total coverage 98.21%,
  above the 80% threshold.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 76 files already formatted.
- `uv run mypy src`: PASS; no issues in 34 source files.
- `uv build --offline`: PASS; source distribution and wheel built.

The earlier Codex GUI asyncio timeout remains an unresolved discrepancy with an
unconfirmed root cause; the verification commands above completed successfully in
this run. This correction is recorded in the commit history of
`feat/2.5-lifecycle` and was included in PR #1, which has merged into `main`.

## Task 2.6 implementation (committed, pushed, verified, and merged)

Added generic `BaseAgent[InputT, OutputT]` as a public `LifecycleComponent` subclass
with default no-op lifecycle hooks and abstract `_execute`. `run()` admits work only
while STARTED, returns the raw typed value, passes through `AgentError` and
control-flow exceptions, and wraps unexpected ordinary errors with a safe message
and chained cause. It does not retry or impose a timeout. The existing `Agent`
protocol, `AgentContext`, `AgentResult`, and `EchoAgent` are unchanged. The run-state
check is only an admission check: shutdown may complete while execution is awaiting.

### Codex-executed verification

- `uv sync --locked --extra dev`: PASS; 83 packages audited.
- `uv run pytest tests/unit/agents/test_agent.py -q --no-cov`: PASS; 18 passed.
- `uv run pytest -q`: PASS; 97 passed; total coverage 98.30%, above the 80%
  threshold. `src/agentos/agents/base_agent.py` has 100% statement coverage.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 77 files formatted.
- `uv run mypy src`: PASS; no issues in 35 source files.
- `uv run mypy tests/unit/agents/test_agent.py`: PASS; checked the protocol
  assignment example in 1 source file.
- `uv build --offline`: PASS; source distribution and wheel built.
- `git diff --check` on the Task 2.6 files: PASS.

All Task 2.6 verification above completed in the Codex environment; no user-executed
verification was needed. The prior Task 2.5 GUI timeout remains documented as a
historical discrepancy with an unconfirmed cause. Task 2.6 was committed as
`3a2da6d8a4f2e8fb51f8e577126b47efba015bbf` and pushed to
`origin/feat/2.6-base-agent`. GitHub merged PR #2 into `main` as
`c34c19b5fe592daa3dd26c1de1bf269c38360bee`. The Task 2.7 feature branch is based
on that merge commit. Task 2.8 has not started and requires separate authorization.

## Task 2.7 implementation (committed, pushed, verified, and merged)

Refined the in-process `EventBus` with input validation, `unsubscribe()`,
side-effect-free counts, sequential exact-before-wildcard dispatch, registration
snapshots, and explicit failure/cancellation behavior. Duplicate registrations
remain independent and unsubscription removes one equal registration. The `Event`
model retains its existing fields and mutability while rejecting blank event types;
payloads remain mutable in-process Python mappings. External brokers, persistence,
retries, background workers, and serialization are out of scope.

Before Task 2.7, the unstaged `STATUS.md` and `TASKS.md` changes recorded Task 2.6's
merge into `main` at `c34c19b5fe592daa3dd26c1de1bf269c38360bee`. That handoff
information is preserved. The unrelated edits to `.gitignore`, `AGENTS.md`,
`README.md`, and `pyproject.toml` are also preserved; `uv.lock` is unchanged.

### Codex-executed verification

- `uv sync --locked --extra dev`: PASS; 83 packages audited.
- `uv run pytest tests/unit/events -q --no-cov`: PASS; 20 passed in 0.13 seconds.
- `uv run pytest -q`: PASS; 115 passed in 0.60 seconds; repository coverage
  98.44%, above the 80% threshold.
- EventBus and Event modules: 100% statement coverage.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 78 files formatted.
- `uv run mypy src`: PASS; no issues in 35 source files.
- `uv build --offline`: PASS; source distribution and wheel built.
- `git diff --check` on Task 2.7 files: PASS. A whole-working-tree check also
  reports the pre-existing trailing blank line in `AGENTS.md`; that unrelated file
  was preserved unchanged.

All checks were Codex-executed; no user-executed verification was needed. The
existing pre-Task-2.7 handoff edits documenting Task 2.6's merge were preserved and
reconciled above. Task 2.7 was committed as
`45482d442243a1a02c4e09c7a93bb0443c466471` and pushed to
`origin/feat/2.7-event-system`. GitHub merged PR #3 into `main` as
`2ad392fc3f0ccc9355ed1d99db05c81d00c50ea1`. The documented concurrency limitation
remains that independent publishes may interleave; event instances and payloads
remain mutable. Task 2.8 is verified and awaits commit approval; Task 2.9 has not
started.

## Task 2.8 implementation (committed, pushed, verified, and merged)

Added a synchronous, type-keyed `ServiceContainer` with instance registration,
lazy singleton and transient factories, explicit nested dependency resolution,
duplicate/missing/cycle errors, and retry after failed singleton creation. A
per-container `RLock` protects registration and resolution; a per-thread resolution
stack detects direct and indirect cycles and is cleared on every factory exit. Factory
exceptions propagate unchanged. `None` instances/results and awaitable factory
results are rejected. The container does not own component lifecycle or disposal and
is not integrated with `Registry` or `Runtime`.

Added `ServiceError(ComponentError)` and public exports from `agentos.base` and
`agentos.container`. Runtime typing for concrete keys is generic. MyPy requires a
typed cast/alias at Protocol and abstract-class token sites because `type[T]` models
instantiable classes; the typed resolution result remains the interface type. This
limitation is documented in the API reference.

### Codex-executed verification

- `uv sync --locked --extra dev`: PASS; 83 packages resolved/audited.
- `uv run pytest tests/unit/container -q --no-cov`: PASS; 19 passed in 0.13 seconds.
- `uv run pytest -q`: PASS; 134 passed in 0.77 seconds; repository coverage 98.71%,
  above the 80% threshold.
- `src/agentos/container/container.py`: 100% statement and branch coverage.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 81 files already formatted.
- `uv run mypy src`: PASS; 37 source files.
- `uv run mypy tests/unit/container/test_container.py`: PASS; 1 test file.
- `uv build --offline`: PASS; source distribution and wheel built.
- `git diff --check` on tracked Task 2.8 files: PASS. The no-index whitespace
  checks on the three new files emitted no whitespace diagnostics (exit 1 reflects
  that each file differs from the empty comparison source).

All checks were Codex-executed in the uv-managed Windows Python 3.14 environment.
The full suite preserves the repository's 80% coverage threshold. The known limits
are synchronous short-running factories, coarse-lock serialization, and no guarantee
against deadlock if a factory waits for another thread that needs this container.
Task 2.8 was committed as `168be89f284f6800493d27d13cad574b2bb87d85` and pushed to
`origin/feat/2.8-service-container`. PR #4 was merged into `main` at
`779dae278a9eb6015bb1791c0090d08a201eef93`. The synchronous factory, coarse-locking,
and MyPy Protocol/abstract-key limitations remain as documented above.

## Task 2.9 — Component Manager (committed, pushed, verified, and merged)

Branch: `feat/2.9-component-manager`, based on Task 2.8 merge commit
`779dae278a9eb6015bb1791c0090d08a201eef93`. Added the standalone asynchronous
`ComponentManager` and tests. It registers explicit lifecycle components by their
existing names, validates forward-referenced dependency graphs and component states
before hooks, initializes and starts in stable topological order, and shuts down or
rolls back in reverse order. A manager asyncio lock serializes operations; recursive
same-task calls fail. Ordinary rollback/shutdown errors are aggregated, and failed
cleanup can be retried with `stop()`. Cancellation and process-control exceptions
propagate without ordinary exception wrapping after best-effort cleanup.

Implementation commit: `f5f72242af4766755cbc0673e048a0a3d8a042a1`, pushed to
`origin/feat/2.9-component-manager`. PR #5 merged into `main` at
`26313e5ea6229883d378f0b2be3ade1bdfe256f6` after CI passed.

The manager does not construct services or integrate with Runtime, EventBus,
ServiceContainer, or BaseAgent execution draining. The existing BaseAgent behavior
remains: an admitted run may finish after manager shutdown. One lifecycle boundary is
inherited from `LifecycleComponent`: `stop()` from `NEW` skips its cleanup hook. If
KeyboardInterrupt or SystemExit interrupts initialization while a component is still
NEW, the manager attempts public `stop()`, but cannot invoke that component's cleanup
hook without bypassing the existing state machine. Repeated interruption can also
interrupt best-effort cleanup; call `stop()` again to retry. When a primary
control-flow exception is followed by ordinary cleanup failures, the primary object
and existing cause are preserved, while cleanup failures are summarized by type in
notes rather than retained as exception objects.

### Codex-executed verification

- `uv sync --locked --extra dev`: PASS; 83 packages resolved/audited after setting
  `UV_CACHE_DIR` to the existing repository `.uv-cache`. The first default-cache
  attempt failed with Windows `os error 183` while creating the cache directory.
- `uv run pytest tests/unit/manager -q --no-cov`: PASS; 36 passed.
- `uv run pytest -q`: PASS; 170 passed; 97.39% repository coverage. The configured
  80% threshold passed. Pytest emitted a nonfatal cache-provider WinError 183 warning.
- `src/agentos/manager/component_manager.py`: 94% combined statement/branch coverage.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 84 files formatted.
- `uv run mypy src`: PASS; no issues in 39 source files.
- `uv build --offline`: PASS; source distribution and wheel built.
- Scoped `git diff --check` and whitespace validation of all seven Task 2.9 files:
  PASS. A whole-tree check reports a pre-existing trailing blank line in unrelated
  `AGENTS.md`; that file was not modified for Task 2.9.

Remaining coverage gaps are lines/branches 116, 140, 199, 204→202, 206–209,
212→211, 214→211, and 216. Lines 116, 140, and 216 are defensive invariants
unreachable through public manager operations. The DFS visited/return paths at 199
and 204–216 are not reached by validated public dependency graphs: Kahn's stalled
residual graph contains cycles, and cycle search returns at the first detected cycle.
No private state was altered to manufacture those paths. Repository coverage is
97.39%, above the required 80% threshold.

Verification above was Codex-executed in the Windows uv-managed Python 3.14
environment. The unrelated edits to `.gitignore`, `AGENTS.md`, `README.md`, and
`pyproject.toml` are preserved. `uv.lock` is unchanged. Task 2.9 is committed and
pushed; those four unrelated modifications remain uncommitted.

## Task 2.10 — Runtime Integration and Orchestration (committed, pushed, verified, and merged)

Branch: `feat/2.10-runtime`, based on Task 2.9 merge commit
`26313e5ea6229883d378f0b2be3ade1bdfe256f6`. Runtime preserves its original four
constructor arguments, imports, `from_settings()` behavior, and synchronous
`start()` operation. New defaulted `services` and `component_manager` fields bind the
Runtime core objects by type after a collision preflight. Existing core keys in a
provided container are rejected without resolving factories; unrelated user service
bindings remain intact. Python generic Registry specializations share the single
runtime `Registry` class key.

Managed lifecycle uses `initialize_async()`, `start_async()`, and `stop_async()` and
delegates state, ordering, rollback, cleanup, and retry to ComponentManager. A private
Runtime lock serializes calls, rejects same-task reentrancy, and leaves manager state
unchanged when a waiter is cancelled; the legacy/managed mixing boundary closes when
a managed request begins. Managed telemetry follows successful transitions, ordinary
telemetry errors are suppressed, and control-flow telemetry exceptions propagate.
Runtime lifecycle events are not published through EventBus. Replacing the public
`services` or `component_manager` fields after construction can break the identity
between Runtime fields and core service bindings. Runtime does not drain in-flight
BaseAgent executions.

The approved compatibility test update in `tests/unit/manager/test_component_manager.py`
replaces the stale assertion that Runtime lacks a manager with assertions that it
owns a separate, empty ComponentManager unaffected by the independent manager under
test. No Task 2.9 implementation file was changed.

### Codex-executed verification

- `uv sync --locked --extra dev`: PASS; 83 packages resolved/audited using the
  existing repository `.uv-cache`.
- `uv run pytest tests/unit/manager -q --no-cov`: PASS; 36 passed.
- `uv run pytest tests/unit/runtime -q --no-cov`: PASS; 27 passed.
- `uv run pytest -q`: PASS; 196 passed; 97.48% repository coverage, above 80%.
- `src/agentos/runtime/runtime.py`: 98% combined statement/branch coverage. The two
  unvisited branches are expected no-telemetry paths on idempotent initialize/start.
- `uv run ruff check .`: PASS.
- `uv run ruff format --check .`: PASS; 84 files formatted.
- `uv run mypy src`: PASS; no issues in 39 source files.
- `uv build --offline`: PASS; source distribution and wheel built.
- Scoped `git diff --check`: PASS.

Pytest emitted a nonfatal Windows cache-provider WinError 183 warning. The earlier
Task 2.9 defensive coverage exclusions remain recorded above. All verification was
Codex-executed in the Windows uv-managed Python 3.14 environment. `.gitignore`,
`AGENTS.md`, `README.md`, and `pyproject.toml` remain preserved; `uv.lock` is
unchanged.

Implementation commit `2b990a2d5d8ec4f7ee86af20f83b34156b041d34` was pushed to
`origin/feat/2.10-runtime`; handoff correction commit
`323def301b80b5f02105ab0c866391360a62f8e4` was also pushed. PR #6 merged into
`main` at `d6afa8a3828ba4d8736d6df0e799a9249f83d559` after CI passed.

## Task 2.11 — Integration Testing and System Validation (implemented, verified, committed, pushed, and merged)

Branch: `feat/2.11-integration-tests`, based on the Task 2.10 merge commit
`d6afa8a3828ba4d8736d6df0e799a9249f83d559`. The integration suite composes
Runtime, explicitly registered in-memory services, named lifecycle components, a
typed BaseAgent, EventBus, Registry, and telemetry through public APIs. No component
discovery or implicit service injection is introduced. Integration verification
uses function-scoped fixtures, explicit dependency injection, deterministic fakes,
and `asyncio.Event` barriers. Existing CLI integration coverage remains unchanged.

The new suite covers all 16 approved P0 scenarios and all 9 approved P1 scenarios.
These include Runtime identity and isolation, lifecycle ordering, agent execution and
domain events, dependency preflight, rollback and retry, cancellation, serialized
concurrency, reentrancy, telemetry boundaries, EventBus fail-fast behavior, and
startup/cleanup exception chaining. P2 legacy CLI compatibility is covered by the
existing `tests/integration/test_agriflow_cli.py`; no duplicate CLI test was added.
No production contract defect was identified. The tests assert the existing
limitations: ServiceContainer does not dispose services, direct manager operations
bypass Runtime telemetry, cleanup may need retry after cancellation, and admitted
BaseAgent work is not drained by Runtime shutdown.

### Codex-executed verification

- `uv --cache-dir .uv-cache sync --locked --extra dev`: PASS; 83 packages resolved
  and audited. The default uv cache path first failed with Windows WinError 183;
  using the repository cache succeeded. No lockfile changes were made.
- `uv --cache-dir .uv-cache run pytest tests/integration -q --no-cov`: PASS; 26
  passed, including the existing CLI test and 25 new integration test cases.
- `uv --cache-dir .uv-cache run pytest -q`: PASS; 221 passed; 97.57% repository
  coverage, above the required 80%.
- Runtime statement/branch coverage: 99%; the remaining partial branch is the
  defensive `stop_async()` error path where the manager raises before reaching
  `FAILED`, so Runtime intentionally omits failure telemetry. Public manager failure
  paths exercised here settle in `FAILED` before Runtime reports them.
- ComponentManager statement/branch coverage: 94%; the documented defensive and
  unreachable graph-cleanup branches remain unchanged from the approved baseline.
- Concurrency module: 6 passed in each of five separate pytest invocations (30
  successful test executions total); no timing sleeps or pending tasks were used.
- `uv --cache-dir .uv-cache run ruff check .`: PASS.
- `uv --cache-dir .uv-cache run ruff format --check .`: PASS; 89 files formatted.
- `uv --cache-dir .uv-cache run mypy src`: PASS; 39 source files.
- `uv --cache-dir .uv-cache build --offline`: PASS; source distribution and wheel
  built.
- Scoped `git diff --check` for the Task 2.11 test and documentation files: PASS.
- No tests were skipped or marked xfail.

Pytest emitted the known nonfatal Windows cache-provider WinError 183 warning for
`.pytest_cache_temp`. The four unrelated working-tree changes remain preserved, and
`uv.lock` remains unchanged. Implementation commit
`20129d0c42c7eddaf17c99426cc2f94c21f3854c` was pushed to
`origin/feat/2.11-integration-tests`. The handoff correction commit
`3c35088f8a6065204dc6a1f8b1472fac64ed4d6f` was also included in PR #7. PR #7 was
merged into `main` at `8daf6db6e7685ddc2ac2eaa278525f948d075705` after GitHub Actions
CI passed. The recorded test and coverage results above are historical Task 2.11
verification, not fresh Task 2.12 release-candidate evidence.

## Task 2.12 — Sprint 2 Release Preparation and Verification (historical pre-release record)

Planning and implementation are limited to a provisional `v0.1.0` Alpha release.
The release branch is `release/sprint-2`, based on merged Task 2.11 commit
`8daf6db6e7685ddc2ac2eaa278525f948d075705`. No release tag or GitHub Release exists.
The current package metadata remains version `0.1.0` and requires Python `>=3.13`.

Release preparation updates the locked CI and tag-build workflows, adds the
`CHANGELOG.md`, aligns the getting-started tutorial, reconciles this handoff, adds
the explicit `health` CLI subcommand while preserving root invocation, and defines
a constrained Hatchling sdist inclusion/exclusion policy.
README correction was not applied because the needed checkpoint text overlaps the
user's pre-existing uncommitted README changes; those edits remain preserved for
separate review. `apps/agriflow/main.py` and its existing integration test were
modified for the CLI correction. The Hatchling sdist configuration is the only
change in `pyproject.toml`; the pre-existing pytest cache setting remains intact.
Dependency declarations and `uv.lock` are unchanged.

### Task 2.12 verification — working-tree candidate, Windows 11 / Python 3.14.0

The candidate was `HEAD=8daf6db6e7685ddc2ac2eaa278525f948d075705` plus the
uncommitted Task 2.12 release-preparation and blocker-remediation edits. The four
pre-existing local modifications remain preserved. `uv.lock` did not change.

- `uv --cache-dir .uv-cache sync --locked --extra dev`: PASS; 83 packages audited.
  The sandboxed attempt could not reach PyPI for Hatchling; the same command passed
  when run with network access. No dependency or lock changes resulted.
- `uv --cache-dir .uv-cache run pytest -q`: PASS; 224 passed, 97.58% coverage
  (80% minimum). Nonfatal pytest cache-provider WinError 183 warning persisted.
- `uv --cache-dir .uv-cache run pytest tests/integration -q --no-cov`: PASS; 26
  passed before CLI regression additions; 29 passed after the additions.
- `uv --cache-dir .uv-cache run pytest tests/e2e -q --no-cov`: PASS; 1 passed.
- `uv --cache-dir .uv-cache run pytest tests/integration/test_agriflow_cli.py -q
  --no-cov`: PASS; 4 passed, covering root invocation, `health`, help, and invalid
  command behavior.
- Five separate runs of `tests/integration/test_runtime_concurrency.py`: PASS; 6
  tests each run (30 successful executions). Each run emitted the same nonfatal
  pytest cache warning.
- `uv --cache-dir .uv-cache run ruff check .`: PASS.
- `uv --cache-dir .uv-cache run ruff format --check .`: PASS; 90 files formatted.
- `uv --cache-dir .uv-cache run mypy src`: PASS; 39 source files.
- `uv --cache-dir .uv-cache build --offline`: PASS; sdist and wheel built.
- `uv --cache-dir .uv-cache lock --check`: PASS; 83 packages resolved.
- `uv --cache-dir .uv-cache run agriflow`: PASS; prints the existing health output.
- `uv --cache-dir .uv-cache run agriflow health`: PASS; prints the same output.
- `uv --cache-dir .uv-cache run agriflow --help`: PASS; lists `health`.
- Installed-wheel public imports and CLI: PASS in a fresh temporary Python 3.14
  environment outside the checkout; imported `agentos` and `apps.agriflow` paths
  resolve from that environment's `site-packages`. Both `agriflow` and
  `agriflow health` work, and help lists the subcommand. `uv run` emitted its
  expected warning that no project was present in the isolated directory.
- Wheel metadata inspection: PASS for name `agentos-agriflow`, version `0.1.0`,
  Python requirement `>=3.13`, and entry point
  `agriflow = apps.agriflow.main:app`. The wheel contained 40 AgentOS and 4 app
  files. Installed distribution metadata and console entry point matched.
- Sdist inspection: reduced from 2,926 members to 105. `node_modules`, frontend
  build output, virtual environments, caches, `.env*`, key, and credentials-pattern
  files were absent. Required Python packages, examples, docs, frontend source,
  packaging metadata, changelog, and lockfile remained present. Both `.env.example`
  templates were locally inspected; sensitive-like settings were empty and neither
  template was packaged. The root README in this sdist matches the current local
  README edits, not committed `HEAD`; because those user-owned changes were excluded
  from this task, this dirty-tree archive is not a release artifact. Rebuild from a
  clean, approved source revision after resolving the README conflict. No credential
  values were printed.
- `uv --cache-dir .uv-cache lock --check`: PASS; 83 packages resolved.
- Scoped `git diff --check`: PASS. Git reported only expected LF-to-CRLF working
  copy notices; the unrelated `AGENTS.md` whitespace warning is preserved.
- GitHub Actions execution remains pending until the branch is pushed and a PR is
  opened.

### Targeted dependency remediation and security review — 2026-11-04

The four approved packages were upgraded using targeted `uv lock --upgrade-package`
options. No dependency declarations in `pyproject.toml` were changed. The resolver
changed exactly seven lock entries:

- `langgraph`: `1.2.10` → `1.2.19` (direct runtime dependency; requested advisory fix).
- `langgraph-sdk`: `0.4.2` → `0.4.12` (transitive runtime dependency of LangGraph;
  requested advisory fix).
- `urllib3`: `2.7.0` → `2.8.0` (transitive runtime dependency via Requests / LangSmith;
  requested advisory fix).
- `pydantic`: `2.13.4` → `2.14.2` (direct runtime dependency; requested advisory fix).
- `langgraph-checkpoint`: `4.1.1` → `4.3.1` (transitive runtime dependency required
  by the selected LangGraph release).
- `pydantic-core`: `2.46.4` → `2.50.2` and `typing-inspection`: `0.4.2` → `0.4.5`
  (transitive runtime dependencies required by Pydantic 2.14.2).

The project requires Python `>=3.13`. The locked dependency graph resolves for both
Python 3.13 and 3.14 via `uv tree --locked --python-version`; the available test and
isolated wheel environment is Python 3.14.0. No Python 3.13 interpreter was used for
execution verification.

Manual review of maintainer advisories for the approved package set and directly
related LangChain/LangGraph dependencies found:

- The original High urllib3 HTTPS proxy TLS advisory
  ([GHSA-8988-9cw3-xx77](https://github.com/advisories/GHSA-8988-9cw3-xx77)), the
  High unbounded streaming chunk-size advisory
  ([GHSA-vxq7-64xx-v4gw](https://github.com/advisories/GHSA-vxq7-64xx-v4gw)), and
  Moderate chunked-Deflate loop advisory
  ([GHSA-gh4c-6fx4-qh6g](https://github.com/advisories/GHSA-gh4c-6fx4-qh6g)) are
  fixed by 2.8.0. The High conditions concern HTTPS proxy TLS configuration or
  unbounded streaming input; the patched version is in the lock.
- The original Moderate LangGraph SDK streaming advisory
  ([GHSA-3fx2-cqw9-xr3c](https://github.com/advisories/GHSA-3fx2-cqw9-xr3c)) is
  fixed by SDK 0.4.6 and LangGraph 1.2.14; selected versions are 0.4.12 and 1.2.19.
  A separate High SDK custom-auth advisory
  ([GHSA-fvww-7h3r-vfhp](https://github.com/advisories/GHSA-fvww-7h3r-vfhp)) affected
  versions through 0.4.3 and was fixed in 0.4.4; 0.4.12 is outside that range.
- The LangGraph checkpoint JSON-deserialization advisory is fixed in
  `langgraph-checkpoint>=4.1.1`; the unsafe msgpack/cache advisories are fixed at
  versions below the selected 4.3.1. The separate Postgres/SQLite checkpoint store
  packages covered by the namespace advisory are absent from this lock.
- `langchain-core==1.5.3` is above the patched versions for the reviewed High
  deserialization ([GHSA-pjwx-r37v-7724](https://github.com/advisories/GHSA-pjwx-r37v-7724))
  and legacy prompt path-traversal
  ([GHSA-qh6h-p6c9-ff54](https://github.com/advisories/GHSA-qh6h-p6c9-ff54))
  advisories. Those code paths require attacker-controlled serialized inputs or
  legacy prompt file paths; no conclusion is made about all possible dependency
  behavior.
- Pydantic 2.14.2 is the published fix for the identified Moderate extra-data
  ([GHSA-qpmf-fgh3-ff25](https://github.com/advisories/GHSA-qpmf-fgh3-ff25)), aliased
  TypedDict/dataclass ([GHSA-3r8g-cqwr-jr29](https://github.com/advisories/GHSA-3r8g-cqwr-jr29)),
  Pydantic V1 dataclass ([GHSA-r49w-vh47-r4hf](https://github.com/advisories/GHSA-r49w-vh47-r4hf)),
  `unique_items` ([GHSA-49g6-96jj-f7r9](https://github.com/advisories/GHSA-49g6-96jj-f7r9)),
  and duration validation ([GHSA-jfv7-ghgv-gx4x](https://github.com/advisories/GHSA-jfv7-ghgv-gx4x))
  advisories. The Fraction exponent and multi-host URL issues were fixed in 2.14.0,
  also included in 2.14.2.
- `pydantic-settings==2.14.2` remains at the fix for its nested-secrets symlink
  advisory; the affected settings source is not used by this application.

The updated graph was resolved and tested, and no Critical or High advisory was
identified in the manually reviewed packages at their selected versions. This is
not a full inventory scan: the user declined transmitting the 83-package inventory
to an external advisory service, and no local advisory database/tool was available.
Consequently, severity counts, remaining findings, and false-positive dispositions
for all locked packages are unavailable. Do not represent this lock as comprehensively
security-cleared.

The targeted update was limited to the four authorized packages and resolver-required
transitives; there were no unexpected major-version changes. The wheel and sdist were
rebuilt offline. The sdist still contains the preserved uncommitted README content,
so it must be rebuilt from a clean, approved source revision after README reconciliation.
`pyproject.toml` and the existing release-preparation changes remain otherwise
unchanged by this remediation.

At this 2026-11-04 checkpoint, the release gate remained **NO-GO**: comprehensive advisory scanning was declined and outstanding; GitHub Actions had not run on these workflow changes; the README checkpoint conflict remained unresolved; the dirty-tree sdist was not a release artifact; and final tag/publication approvals were outstanding. This is a historical checkpoint; see the 2026-11-11 security remediation update below. No tag, GitHub Release, package publication, or Sprint 3 work had been started.

## Task 2.12 — Critical certifi remediation and offline security verification — 2026-11-11

This is a verified isolated patch at candidate baseline `a68db391027b5b242f96daad337ffa76d6556a54`; it is not yet transferred to or verified as a committed `release/sprint-2` revision. The new security worktree is `C:\Users\USER\AppData\Local\Temp\agentos-security-remediation-a68db391`. Its only intended changes are `uv.lock`, this file, and `docs/handoff/TASKS.md`. The original checkout and the separate README correction worktree remain untouched.

The refreshed lock changes exactly one package record: `certifi` `2026.7.22` → `2026.10.23`. The prior version was affected by GHSA-6q48-6c7w-9gw2 / PYSEC-2026-4320, with affected versions below `2026.10.18`; `2026.10.23` is beyond that range. No dependency declarations, package count, or graph edges changed. The source isolated lockfile SHA-256 and transferred worktree lockfile SHA-256 are both `0FAC88D3F3C77C392DBCCEBB47E8DBEDE2B8AE81BC872F4E59F8D9EEA58CBA6A`. Baseline lock SHA-256 was `171152e784d72468ee33f580ab228003c6b0b74e0c1512f9f1cb6a6bea428512`.

The local-only audit used verified OSV-Scanner v2.7.0 Windows x64 (SHA-256 `9964ed64ec9a387391eb4cc006ad5c531154821aef29b793e02c448de4686438`; SLSA provenance verified) and the official PyPI OSV archive at `https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip`. The refreshed snapshot was retrieved 2026-11-11; archive SHA-256 `13F7BEA3C98240F0C26BF4383D215BC13251DF414225F271DFCC02C14F35297F`; GCS MD5/CRC32C and ZIP integrity checks passed. Full offline mode used the local database. The scan exited 0 and reconciled all 82 third-party lock records (83 records including the project): zero missing, extra, duplicate, unsupported, or unmatched records and zero matched advisories. This result describes that snapshot and scanner coverage; it is not a guarantee against unknown advisories. No package inventory was sent to an external service. Full offline mode and restricted execution were used, but no independent firewall or packet-capture evidence was collected.

The exact updated lock was verified in isolated copies on Python 3.13.14 and 3.14.0: each full suite passed (224 tests, 97.58% coverage), 29 integration tests passed, one E2E test passed, Ruff lint/format and MyPy passed, and offline sdist/wheel builds passed. The installed wheel was separately verified in a clean Python 3.14 environment: `uv pip check`, installed package imports/metadata, and both CLI invocations passed. These are isolated verification results, not results from the release branch.

Historical checkpoint (2026-11-11): release status was **NO-GO** while README reconciliation, PR CI, merge, tag, and publication approvals were still pending. This pre-release status is superseded by the post-release closure entry below.

## Landing page publication to GitHub — 2026-10-26

User explicitly requested pushing the previously created landing page to GitHub.
Integrated it as standalone `landing-page/` on top of current `main`, preserving
all Python framework/application sources and existing Git history. This is separate
from the numbered framework tasks; no next framework task was started.

Acceptance: preserve existing project, reproduce the frontend build, verify the
landing-page interactions and graphics, and push the approved page to GitHub.
Includes local SVG artwork, responsive styling, agent/project dialogs, dependency
lockfile, and usage instructions. Live AI services and public website deployment
are not included. Google Fonts is optional with a sans-serif fallback.

Current cloud verification (all exit 0):
- `cd landing-page && npm ci --cache /workspace/.npm-cache --no-audit --no-fund`.
- `cd landing-page && npm run build` — Vite 6.4.5 production build passed.
- Headless Chromium via temporary Playwright runner: all three agent dialogs,
  project dialog, mobile menu, images, and overflow checks at widths 375/768/1440
  passed; no JavaScript errors. Runner was outside the checkout.
- `UV_CACHE_DIR=/workspace/.uv-cache uv sync --locked --extra dev`.
- `UV_CACHE_DIR=/workspace/.uv-cache uv run pytest -q` — 60 passed, 98.31% coverage.
- `UV_CACHE_DIR=/workspace/.uv-cache uv run ruff check .` — passed.
- `UV_CACHE_DIR=/workspace/.uv-cache uv run ruff format --check .` — 73 files passed.
- `UV_CACHE_DIR=/workspace/.uv-cache uv run mypy src` — 33 source files passed.

Only the landing-page files and this evidence entry are included in this change.
No credentials or generated build/dependency directories are included.

## Sprint 2 administrative closure — Task 2.13 — 2026-11-13

**Authoritative post-release status:** Sprint 2 is complete. Task 2.12 v0.1.0 Alpha is published as a GitHub pre-release. No package was published to PyPI or another registry. The release is not production-ready. Earlier pre-release NO-GO entries above are historical checkpoints and are retained as such.

### Merge and governance evidence

- PR [#8 — Sprint 2 v0.1.0 Alpha Release Candidate](https://github.com/anfazmzbd-aus/ai-agriflow/pull/8) merged into main using a standard merge commit.
- Approved PR head: 77b9d105779ef8919b1bc3b7a34bb318f2118a19.
- Merge commit and current main: 073bfb796e473715f1b42f99aa32afe32fdfda1c.
- The owner-verified GitHub merge record reported branch protection enabled; CI passed before merge. No force-push or history rewrite was used.
- Annotated tag v0.1.0 has tag-object SHA da4a6f780549a3655c28fcd7c84a44102d0a34ad and peels to 073bfb796e473715f1b42f99aa32afe32fdfda1c.

### Published release and assets

- [AgentOS AgriFlow v0.1.0 Alpha](https://github.com/anfazmzbd-aus/ai-agriflow/releases/tag/v0.1.0), GitHub Release ID 443538987; published 2026-11-12 21:39:16 UTC, draft=false, prerelease=true, excluded from Latest.
- Release workflow 43287980180 completed successfully on target commit 073bfb796e473715f1b42f99aa32afe32fdfda1c.
- Exactly two distribution assets are attached. Their hashes were verified against the workflow-produced artifacts and again after release download:
  - agentos_agriflow-0.1.0-py3-none-any.whl — SHA-256 b7660f710d00f33d9cd6f5d6182a5e12d41130ad7f9939a3e370aadde9a00d03 (32,680 bytes).
  - agentos_agriflow-0.1.0.tar.gz — SHA-256 bc773695d11422be3413cd333b919890f1a49539ebcff8a4dcb3e297c15f743a (164,812 bytes).
- No release asset was rebuilt or substituted for publication.

### Verification evidence and execution contexts

- **GitHub Actions:** Release workflow 43287980180 ran the tagged revision on Python 3.13, passed its verify-and-build job, and uploaded the review artifact. The recorded clean-source candidate matrix reports 224 tests passed at 97.58% coverage, 29 integration tests, one E2E test, Ruff lint/format, MyPy, and offline sdist/wheel build on Python 3.13.14 and Python 3.14.0. The earlier handoff records the matrix as run in isolated environments but does not preserve an executor attribution for each matrix row; do not retroactively label those rows USER-EXECUTED or CODEX-EXECUTED.
- **Tagged wheel acceptance — CODEX-EXECUTED:** Installed the exact published wheel in a fresh isolated Windows CPython 3.14.0 environment using hash-checked, lock-constrained runtime dependencies. Distribution metadata reported version 0.1.0; certifi was 2026.10.23; uv pip check passed with 47 packages. agentos and apps.agriflow resolved from the temporary environment's site-packages. agriflow, agriflow health, and agriflow --help each exited 0. The downloaded wheel and sdist hashes matched the values above.
- **Earlier candidate checks:** The 224-test / 97.58% results, 80% minimum coverage gate, 29 integration tests, one E2E test, Ruff, formatting, MyPy, and offline build remain historical candidate verification evidence. They are not a newly rerun post-publication suite.

### Security audit scope and limits

The local offline OSV-Scanner v2.7.0 scan on 2026-11-11 used a refreshed official PyPI advisory snapshot and the exact candidate lockfile. It reconciled 82 of 82 third-party package records and reported zero matched advisories for that database snapshot and scanner coverage. The audit did not establish absence of unknown, unpublished, or future advisories; the manual advisory review was also scoped, not comprehensive. Full offline mode was used, but no independent firewall or packet-capture evidence was collected. No dependency inventory was sent to an external service. Continue routine advisory monitoring and targeted dependency maintenance.

### Remaining limitations and maintenance

- AgentOS is an early-stage framework; AgriFlow is a reference application, not a production agriculture platform.
- Runtime does not drain in-flight BaseAgent executions; public service and manager references can be reassigned, breaking core service-binding identity.
- Direct ComponentManager lifecycle calls bypass Runtime serialization and telemetry. Cancellation can interrupt cleanup, and stopping a LifecycleComponent from NEW skips its stop hook.
- Event delivery is in-process and fail-fast; concurrent publications may interleave. Event payload objects are not deep-frozen, so consumers must treat shared payload data as immutable during dispatch.
- ServiceContainer does not initialize, stop, or dispose registered services. The wheel includes agentos and apps; docs and examples remain in the sdist or repository.
- Durable workflows, distributed orchestration, and production agricultural integrations are not included.

### Sprint status

Sprint 2 Tasks 2.3.2 through 2.12 are complete at the recorded integration/release checkpoints; the reconstructed 2.3.1 baseline caveat remains. Task 2.13 is this documentation-only administrative handoff and draft-plan preparation. Sprint 3 is proposed only; no Sprint 3 implementation is authorized or started.

## Sprint 3 — Task 3.1 workflow graph model and validation

### Historical Debian checkpoint — superseded by the Windows checkpoint below

Architecture and implementation were approved. The implementation is pending
locked verification and separate commit approval. It adds an immutable DAG,
declaration-order topological sorting, and `WorkflowGraphError`. The existing
linear runner, lifecycle dependency handling, runtime, and adapter are outside
the change.

- Baseline: GitHub `main` at `cd9a6c35203bb4c2c7a2dc5d71cacec7a861afcf`.
  The isolated shallow checkout was reconstructed from GitHub and its commit and
  tree hashes matched. The original Windows checkout was outside this session.
- Codex execution context: Debian 13, CPython 3.13.5, uv 0.13.6.
  `uv run --locked --no-sync python --version` exited 0.
- `uv sync --locked --extra dev --offline` exited 2 because a locked artifact
  was absent from the uv cache. An online retry with `UV_HTTP_TIMEOUT=6` and
  `UV_HTTP_RETRIES=0` exited 2 after timing out on a locked wheel download.
- `uv run --locked --no-sync pytest -q --no-cov tests/unit/workflows tests/unit/adapters tests/unit/manager`
  and `uv run --locked --no-sync pytest -q` both exited 2 because pytest was
  unavailable. No current coverage measurement is available.
- `uv run --locked --no-sync ruff check .`, `uv run --locked --no-sync ruff format --check .`,
  `uv run --locked --no-sync mypy src`, `uv run --locked --no-sync mypy`, and
  `uv run --locked --no-sync mkdocs build --strict` each exited 2 because the
  corresponding executable was unavailable.
- `uv build --offline` exited 2 because Hatchling was absent from the cache.
  No wheel was produced for the installed-wheel import check.
- A standard-library smoke harness run with `uv run --locked --no-sync python -`
  exited 0. It used the actual workflow and base subpackages with a temporary root
  package namespace to bypass the unavailable configuration dependencies. A
  brute-force permutation oracle covered all 4,096 loop-free directed graphs on
  four labeled nodes, accepting 543 DAGs in the expected order and rejecting
  3,553 cyclic graphs. The harness also passed deep-chain, deep-cycle, malformed
  input, immutability, safe diagnostics, linear example, and adapter checks.
- `uv run --locked --no-sync python -m compileall -q src apps tests` and
  `git diff --check` exited 0.

### Current Windows checkpoint — verified candidate, not committed — 2026-11-16

Task 3.1 is implemented and technically verified, pending final diff review and
explicit staging/commit authorization. Task 3.2 has not started and remains
unauthorized. The earlier Debian results above are historical environment results,
superseded for candidate acceptance by the Windows evidence below; they have been
preserved rather than represented as successful runs.

The candidate is in `E:\Projects\ai-agriflow-task-3.1`, with detached HEAD at
`cd9a6c35203bb4c2c7a2dc5d71cacec7a861afcf`. It introduces graph declarations,
immutable validated DAG topology, deterministic declaration-order topological
sorting, and the public graph exception. No DAG execution, runtime/lifecycle
integration, application coupling, dependency declaration, or lockfile change is
included. Existing linear workflow APIs remain available.

#### Verification provenance

- **CODEX GUI — completed Windows checks, supplied by the user:** CPython 3.14.0;
  process-local `UV_CACHE_DIR=E:\Projects\.uv-cache-agentos`. Focused graph tests:
  **27 passed**; full suite: **251 passed**; repository coverage: **97.87%**, above
  the configured **80%** gate; graph module coverage: **100%**. Ruff lint,
  formatting, MyPy, and strict MkDocs passed. Hatchling **1.33.0** was recovered
  under the declared `hatchling>=1.25` build requirement; offline wheel and sdist
  builds and installed-wheel acceptance succeeded. These are GUI-executed results,
  not tests rerun by Codex CLI. Raw test, coverage, quality-check, backend-recovery,
  and build command logs were not inspected by CLI; exact commands, exit codes,
  timings, and build-warning text are not inferred from the reported passes.
- **GUI acceptance evidence inspected by CODEX CLI:**
  `C:\Users\USER\AppData\Local\Temp\agentos-task31-packaging-2f444f63bfc54881ae3fc1df74231254\acceptance-report.json`
  and its `verify_candidate.py` script. The report records isolated Windows
  CPython 3.14.0 imports from `wheel-env\Lib\site-packages`, package metadata
  `agentos-agriflow==0.1.0` / Python `>=3.13`, and all 47 installed distribution
  versions matching approved lock records. It records valid archives (50 wheel
  members, 107 sdist members), selected candidate-byte comparisons, typing marker
  and source/test inclusion, and generated/credential-pattern exclusions.
  The positive graph order is `metrics, database, consumer, cache`; the negative
  cycle raises `WorkflowGraphError`. `agriflow`, `agriflow health`, and
  `agriflow --help` each have recorded exit code 0 and empty stderr.
  Dependency consistency passed according to the GUI handoff; the JSON records
  lock alignment but does not contain a separate dependency-check command log.
- **CODEX CLI — independent read-only verification:** all nine pre-edit candidate
  SHA-256 fingerprints matched the previously recorded values; HEAD matched the
  exact baseline; staging was empty; `pyproject.toml` and `uv.lock` were unchanged.
  CLI independently recalculated the wheel and sdist hashes and matched them to
  both the inspected report and user-provided values. CLI inspected the report
  and script without rerunning the GUI acceptance script or implementation tests.
  Earlier local availability probes returned Python 3.14.0, `LOCAL_EXECUTION_OK`,
  and pytest 9.1.1 using the process-local alternative cache.

#### CODEX CLI handoff documentation verification

With process-local `UV_CACHE_DIR=E:\Projects\.uv-cache-agentos` and
`PYTHONDONTWRITEBYTECODE=1`, CLI ran
`uv run --locked --no-sync --offline mkdocs build --strict --site-dir <temporary-output>`.
The first post-edit run exited 0, writing to
`C:\Users\USER\AppData\Local\Temp\agentos-task31-handoff-docs-b1f7fcb2f4cf49bead7cc67464e2acd5`.
The command output was inspected directly. It printed a Material for MkDocs
advisory banner about future MkDocs 2.0 compatibility and INFO notices for pages
outside the configured navigation; strict verification still succeeded. The
banner is recorded as tool output, not an independently assessed dependency claim.
`git diff --check` also completed without findings. After recording this evidence,
strict MkDocs and the diff check must pass again on the final handoff text.

#### Local candidate artifacts

These are local Task 3.1 candidate artifacts, not published Sprint 2 release
artifacts. They are under the acceptance-report directory's `dist` subdirectory.

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| `agentos_agriflow-0.1.0-py3-none-any.whl` | 34,777 | `39c66114bc38a5b6be85b9eed5e6b857652f91cdf24521a725fa76c726ecf613` |
| `agentos_agriflow-0.1.0.tar.gz` | 172,604 | `d0aecf53673a63eeded92e5bc97ca767d0c6b1a68988b85065da7ef32087c6d8` |

#### Verified candidate fingerprints before handoff reconciliation

All nine matched before this documentation-only reconciliation. Only
`docs/handoff/STATUS.md` and `docs/handoff/TASKS.md` are authorized to change
during reconciliation; the following hashes for those two files identify the
earlier GUI-verified candidate, not the final handoff text. Final handoff hashes
are reported separately after editing, avoiding a self-referential hash.

| Path | Pre-reconciliation SHA-256 |
| --- | --- |
| `docs/api/agentos.md` | `092adfb005a673ac77b30c7bdd4209dacf4b8759f0274ffa9f9a548836eab8d3` |
| `docs/architecture/overview.md` | `14ec8f029f7a0e2ceed242389bef749575e07dc32473f95982fdd79386d07978` |
| `docs/handoff/STATUS.md` | `2f017729c69ff8d92ff8ef3951b1247eaa11ced43f670dd80bb4e1dbb053899e` |
| `docs/handoff/TASKS.md` | `326b217ee927bb83af1fc457054dd06f2917415f87a395b4fbd69e2b79c7f5b3` |
| `src/agentos/base/__init__.py` | `9ebb04c780a60cf34d5715a47a3e2e96763071765684796847837f842d590f8d` |
| `src/agentos/base/exceptions.py` | `0d8a00692c8cbfeb7a07f8721d823e34f10e5805790bb94a6bc64bcfaf0553d2` |
| `src/agentos/workflows/__init__.py` | `35cde98ee0b46f28ea21f70c229dedb08c49c7e4ee986b41b6e0dc19b2f428a0` |
| `src/agentos/workflows/graph.py` | `c342bee9abc9d157e62310191b67feaf2edd18b5769e1a3ed86ea30170c79bf5` |
| `tests/unit/workflows/test_graph.py` | `f766b0ecfbd0e3725c55702ad4129d5e4cf0288dfdcffa0243891c049762f9e9` |

#### Warnings, limitations, and remaining gate

- The default uv cache produced an initialization error in restricted execution.
  Elevated metadata inspection found an ordinary directory; the exact root cause
  remains unconfirmed. The alternative cache is process-local; no default-cache
  deletion or permission repair was performed.
- `site/` contains 60 acknowledged generated MkDocs output files. It is explicitly
  excluded from any eventual Task 3.1 commit and is left untouched. Documentation
  verification during reconciliation must use a temporary output directory.
- Earlier Debian dependency/download failures are retained above. Missing raw GUI
  logs limit reconstruction of exact commands and warnings; no claim of a
  warning-free build is made.
- Graph construction validates plain string IDs and exact node/tuple shapes.
  `NodeId` is a static type, not a distinct runtime wrapper. Graphs are immutable
  through supported public operations; deliberate low-level frozen-dataclass
  bypasses are outside that guarantee. Cycle diagnostics expose no cycle path.
- Review found no blocking graph correctness or compatibility defect. Additional
  tests for malicious subclasses/custom sequences and cross-module static typing
  examples would strengthen coverage; 100% reported module coverage does not
  prove every possible runtime input.
- Sprint 2 runtime, lifecycle, event-delivery, and service-container limitations
  remain as documented above. This task adds topology validation only.
- Other documents (including the draft Sprint 3 plan and AGENTS checkpoint) retain
  historical planning language; they were outside this reconciliation's edit
  authorization. This current checkpoint governs Task 3.1 status.
- The historical “Sprint 3 proposed only” statement in the Task 2.13 closure above
  describes that checkpoint. Task 3.1 now has separate authorization and evidence;
  this does not authorize Task 3.2 or any release.
- Final handoff diff review and explicit staging/commit authorization remain
  required. Nothing has been staged or committed; HEAD remains the baseline.

## Sprint 3 — Task 3.2 — candidate implementation — 2026-11-17

The owner separately approved Task 3.2 architecture, the exact 14-file manifest,
implementation, and verification. The candidate is in
`E:\Projects\ai-agriflow-task-3.2` on `feat/3.2-workflow-context`, based on
`4dd8bba682a4a6967d87b88ac62de9e73315b7ca`. GitHub main matched that SHA before
creation. Post-merge Task 3.1 CI run 44008844894 has a successful verify job.
Task 3.1 is merged; earlier uncommitted/detached-head statements describe its
historical candidate checkpoints. Task 3.2 implementation approval supersedes
historical "unauthorized" planning language only for this task. AGENTS.md and the
draft sprint plan remain untouched.

Implemented WorkflowNodeContext, WorkflowNodeHandler, and WorkflowRunState under
agentos.workflows. The run owns an independent record-once store; node views expose
only direct dependencies, with immutable copied mappings. Outcomes retain identity
and all six ExecutionStatus contracts, including successful None. Heterogeneous
lookup returns ExecutionResult[object]. One private erasure cast handles the
existing invariant result generic. Existing graph and linear APIs are unchanged.

No executor, retries, timeout machinery, runtime integration, adapter, dependency,
or lockfile changes are included. Payload references are shallow and treated as
immutable by convention. One coordinator owns writes. Fixed helper messages and
safe representations omit sensitive payloads; caller error strings and full
tracebacks are not automatically sanitized. Contexts are not a Python sandbox.

### Task 3.2 verification

Verification completed in Windows CPython 3.14.0 with uv 0.9.16. See the
current command evidence and final review below.
No commit, push, PR, release change, or Task 3.3 work is authorized.

### Task 3.2 final verification evidence — CODEX GUI EXECUTED

Current Task 3.2 execution: Windows 11, CPython 3.14.0, uv 0.9.16,
pytest 9.1.1, Ruff 0.16.1, MyPy 1.20.2, MkDocs 1.6.1. Process-local
UV_CACHE_DIR=E:\Projects.uv-cache-agentos. These are Codex-executed results,
not user-executed checks or historical Debian results.

Evidence root:
C:\Users\USER\AppData\Local\Temp\agentos-task32-verify-acaef6aca0d947be950de08ce4741d27.
run_gate.ps1, individual logs, gate-exits.txt, archive inventories, the isolated
acceptance script/report, and final fingerprints are retained outside the worktree.
Coverage, final caches, site output, and package output use that directory.
Commands below omit only those explicit temporary cache/output paths, preserved
in the runner and logs. The final fingerprints are external to avoid self-reference.

| Command | Actual exit | Outcome |
| --- | --- | --- |
| uv sync --locked --extra dev --python C:\Python314\python.exe | 0 | Final sync audited 83 packages |
| uv run --locked --no-sync pytest tests/unit/workflows -q --no-cov -o cache_dir=<temporary> | 0 | 60 passed in 8.55s |
| uv run --locked --no-sync pytest -q -o cache_dir=<temporary> | 0 | 282 passed in 7.22s; 98.02% coverage; unchanged 80% gate |
| uv run --locked --no-sync ruff check . | 0 | All checks passed |
| uv run --locked --no-sync ruff format --check . | 0 | 100 files formatted |
| uv run --locked --no-sync mypy src --cache-dir <temporary> | 0 | 41 source files passed |
| uv run --locked --no-sync mypy --cache-dir <temporary> | 0 | 44 configured-package source files passed |
| uv run --locked --no-sync mypy tests/typing/workflows_contracts.py --cache-dir <temporary> | 0 | Positive fixture passed |
| uv run --locked --no-sync mypy tests/typing/workflows_contracts_invalid.py --cache-dir <temporary> | 1, expected | Nine intentional errors; pytest verifies source file, line, diagnostic code, stderr and exit |
| uv run --locked --no-sync mkdocs build --strict --site-dir <temporary> | 0 | Evidence-text docs passed; final revision rechecked after recording |
| git diff --check | 0 | No whitespace errors; final revision rechecked after recording |
| uv build --offline --python C:\Python314\python.exe --out-dir <temporary>/dist | 0 | Sdist then wheel-from-sdist built; Hatchling 1.33.0 |
| uv run --locked --no-sync python -m examples.workflow_context | 0 | reference: 7 |

The new context module has 100% statement/branch coverage: 70 statements and
22 branches. No test skips or weakened assertions were used.

Development findings: initial lint exited 1 for new-file formatting, import,
docstring and unused-variable findings; these were repaired within the manifest.
Initial source MyPy exited 1 on invariant ExecutionResult storage. The approved
private erasure cast fixed it without changing core contracts or claiming typed
heterogeneous lookup. The first focused run exited 1 (59 passed, one failed):
the diagnostic parser matched a bracketed type rather than the trailing code.
It was corrected, then strengthened to require the expected source file.
Final focused and full runs passed. An evidence-writing attempt failed before any
write because Windows default decoding was used; explicit UTF-8 fixed that step.
Final diff review also caught earlier default-decoding round trips in TASKS.md
and API docs. Their historical text was restored directly from HEAD as UTF-8
before reapplying only the approved status edits and API addition.

#### Task 3.2 packaging and installed-wheel evidence

The approved cache already contained Hatchling; no backend recovery or dependency
upgrade was needed. Runtime requirements were exported with
uv export --locked --offline --no-dev --no-emit-project --format requirements.txt
--output-file <temporary>/runtime-requirements.txt (exit 0).
A fresh uv-created Python 3.14.0 environment received hash-verified runtime pins
via uv pip install --offline --require-hashes, then the wheel via --offline
--no-deps (all exit 0). Only the candidate wheel was reinstalled after final
archive regeneration. uv pip check exited 0 with 47 compatible packages.

The isolated python -I acceptance harness exited 0. agentos and apps.agriflow
resolved from isolated site-packages; all 47 installed versions matched approved
lock records. Metadata, exports, legitimate None, result identity, independent
runs, snapshots, direct views, immutable maps, duplicate rejection, a typed
async handler, and legacy linear behavior passed. agriflow, agriflow health,
and agriflow --help each exited 0 with empty stderr. No external agricultural
or paid API was invoked.

| Local artifact | Bytes | SHA-256 |
| --- | --- | --- |
| agentos_agriflow-0.1.0-py3-none-any.whl | 36,774 | 83b16dad4c5574979d35aa7e3310e229e9fc8da3977fcac3ac1dcdc3dffd0664 |
| agentos_agriflow-0.1.0.tar.gz | 181,547 | ba73ebbdf931792a6f7333ac5f648a9c9b47c984edcf81e1e6cdcf0a606a1da4 |

Archive checks passed: 51 wheel members, 114 sdist members, typing marker, exact
candidate context/export bytes, and sdist source/test/example/API/metadata/lock
comparisons. Generated/cache/credential-pattern exclusions passed. The existing
sdist policy excludes handoff files, so this evidence-only handoff update does
not invalidate artifact comparisons. These are local, unpublished artifacts. The sdist was rebuilt and its comparisons
rerun after the documentation encoding repair; the wheel checksum stayed unchanged.

#### Task 3.2 final review and limits

All changed tracked and untracked files were reviewed for API compatibility,
snapshot ownership, failure paths, privacy, type erasure, cancellation, tests,
docs, and 14-file scope. No blocking defect was found. One coordinator owns
writes. Payload immutability is by convention; no deep copy, persistence,
eviction, retry replacement, scheduling, timeout machinery, or runtime integration
is included. Directly constructed contexts validate shape but not graph membership.
Private Python attributes and hostile custom Mapping implementations are not a
security sandbox. Caller-supplied errors and full tracebacks can expose data.

Nonfatal output: cross-drive copy fallback, Git LF/CRLF notices, and the Material
for MkDocs advisory banner plus INFO notices for pages outside nav. The banner
is tool output, not an independently verified claim. No configuration was weakened.
The original checkout, Task 3.1 tracked files, and both existing site directories
are compared against pre-edit SHA-256 snapshots in the final external review.
No original checkout files or site output were cleaned, reset, stashed, or edited.
The new worktree has its .venv and initial ignored tool/test caches; final generated
outputs remain external. Protected source contracts, metadata, lockfile, AGENTS,
sprint plan, and releases are unchanged.

Task 3.2 is technically verified; evidence-text docs and whitespace checks passed.
The final revision is rechecked after recording this entry. Explicit staging/commit
approval is still required. Nothing is staged or committed. Push, PR,
merge, releases, and Task 3.3 remain unauthorized.
