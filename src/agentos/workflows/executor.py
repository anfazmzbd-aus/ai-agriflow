"""Sequential DAG execution with explicit ownership and cancellation boundaries."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from agentos.base import WorkflowError
from agentos.core import ExecutionResult, ExecutionStatus
from agentos.workflows.context import WorkflowNodeContext, WorkflowNodeHandler, WorkflowRunState
from agentos.workflows.graph import NodeId, WorkflowGraph


def _is_binding_sequence(value: object) -> bool:
    """Validate runtime collection shape independently of static element types."""
    return not isinstance(value, (str, bytes, bytearray)) and isinstance(value, Sequence)


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class WorkflowNodeBinding[InputT]:
    """Bind one graph-local identity to a typed asynchronous callable."""

    _node_id: NodeId
    _handler: WorkflowNodeHandler[InputT, object]

    def __init__[OutputT](
        self, node_id: NodeId, handler: WorkflowNodeHandler[InputT, OutputT]
    ) -> None:
        """Validate shape without invoking the handler or rendering its values."""
        if type(node_id) is not str or not node_id.strip():
            raise WorkflowError("workflow binding ID must be a plain nonblank string")
        if not callable(handler):
            raise WorkflowError("workflow binding handler must be callable")
        object.__setattr__(self, "_node_id", node_id)
        # Output type erasure is private and one-way. Frozen outcomes are read as
        # object after invocation; no unchecked concrete lookup is exposed.
        object.__setattr__(self, "_handler", cast("WorkflowNodeHandler[InputT, object]", handler))

    @property
    def node_id(self) -> NodeId:
        """Return the immutable graph-local node identity."""
        return self._node_id

    def __repr__(self) -> str:
        """Omit the identifier and callable representation."""
        return "WorkflowNodeBinding()"


class SequentialWorkflowExecutor[InputT]:
    """Execute a validated DAG with one active invocation per instance.

    Bindings are snapshotted before any handler runs. Completed outcomes remain
    available after exceptions or cancellation. Payloads are not deep-frozen,
    and this is not a thread-safe or multi-event-loop writer API.
    """

    __slots__ = ("_active_run", "_graph", "_handlers", "_last_results")

    def __init__(
        self, graph: WorkflowGraph, bindings: Sequence[WorkflowNodeBinding[InputT]]
    ) -> None:
        """Preflight complete bindings and retain no live caller-owned collection."""
        if not isinstance(graph, WorkflowGraph):
            raise WorkflowError("workflow executor requires a WorkflowGraph")
        if not _is_binding_sequence(bindings):
            raise WorkflowError("workflow bindings must be an ordered sequence")
        handlers: dict[NodeId, WorkflowNodeHandler[InputT, object]] = {}
        for position, binding in enumerate(tuple(bindings), start=1):
            if type(binding) is not WorkflowNodeBinding:
                raise WorkflowError(f"invalid workflow binding at position {position}")
            if binding.node_id in handlers:
                raise WorkflowError(f"duplicate workflow binding at position {position}")
            if binding.node_id not in graph.nodes:
                raise WorkflowError(f"extra workflow binding at position {position}")
            handlers[binding.node_id] = binding._handler
        if len(handlers) != len(graph.nodes):
            raise WorkflowError("workflow node bindings are incomplete")
        self._graph = graph
        self._handlers = MappingProxyType(handlers)
        self._active_run: WorkflowRunState[InputT] | None = None
        self._last_results: Mapping[NodeId, ExecutionResult[object]] = MappingProxyType({})

    @property
    def results(self) -> Mapping[NodeId, ExecutionResult[object]]:
        """Snapshot active progress, or return the final retained immutable mapping."""
        if self._active_run is not None:
            return self._active_run.results
        return self._last_results

    async def run(
        self, input_data: InputT
    ) -> ExecutionResult[Mapping[NodeId, ExecutionResult[object]]]:
        """Run nodes in stable order, stopping globally on the first non-success.

        Normal non-success returns aggregate as PARTIAL with the retained map.
        Raised ordinary errors produce a safe node outcome and chained WorkflowError.
        Actual cancellation and process-control exceptions propagate.
        """
        if self._active_run is not None:
            raise WorkflowError("workflow executor already has an active run")
        state = WorkflowRunState(self._graph, input_data=input_data)
        self._active_run = state
        try:
            self._last_results = MappingProxyType({})
            for node_id in self._graph.topological_order():
                # Topological order plus immediate fail-fast means every direct
                # prerequisite recorded before this invocation is SUCCESS.
                context = state.context_for(node_id)
                outcome = await self._invoke(node_id, context, state)
                if outcome.status is not ExecutionStatus.SUCCESS:
                    return ExecutionResult[Mapping[NodeId, ExecutionResult[object]]].partial(
                        state.results, error="workflow execution did not fully succeed"
                    )
            return ExecutionResult[Mapping[NodeId, ExecutionResult[object]]].success(state.results)
        finally:
            try:
                self._last_results = state.results
            finally:
                self._active_run = None

    async def _invoke(
        self,
        node_id: NodeId,
        context: WorkflowNodeContext[InputT],
        state: WorkflowRunState[InputT],
    ) -> ExecutionResult[object]:
        """Invoke one handler and preserve original causes behind safe summaries."""
        try:
            outcome: object = await self._handlers[node_id](context)
        except asyncio.CancelledError:
            state.record_result(
                node_id, ExecutionResult[object].cancelled("workflow node execution cancelled")
            )
            raise
        except TimeoutError as exc:
            state.record_result(
                node_id, ExecutionResult[object].timeout("workflow node execution timed out")
            )
            raise WorkflowError("workflow node execution timed out") from exc
        except Exception as exc:
            state.record_result(
                node_id, ExecutionResult[object].failure("workflow node execution failed")
            )
            raise WorkflowError("workflow node execution failed") from exc
        if not isinstance(outcome, ExecutionResult):
            state.record_result(
                node_id, ExecutionResult[object].failure("workflow node returned an invalid result")
            )
            raise WorkflowError("workflow node returned an invalid result")
        # Runtime validation establishes the result class; generic output types
        # are erased to object without changing the original outcome instance.
        result = cast("ExecutionResult[object]", outcome)
        state.record_result(node_id, result)
        return result

    def __repr__(self) -> str:
        """Omit graph identities, bindings, inputs, and outcomes."""
        return "SequentialWorkflowExecutor()"
