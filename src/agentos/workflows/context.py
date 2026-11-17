"""Per-run result ownership and asynchronous DAG node contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from agentos.base import WorkflowError
from agentos.core import ExecutionResult
from agentos.workflows.graph import NodeId, WorkflowGraph


def _require_node_id(node_id: NodeId) -> None:
    """Reject malformed identities without formatting untrusted values."""
    if type(node_id) is not str or not node_id.strip():
        raise WorkflowError("workflow node reference must be a plain nonblank string")


@dataclass(frozen=True, slots=True, repr=False, eq=False)
class WorkflowNodeContext[InputT]:
    """Read-only node input and a snapshot of direct prerequisite outcomes.

    Payload objects are shared by reference and must be treated as immutable.
    Construct through WorkflowRunState.context_for for graph-scoped visibility.
    Direct construction validates shape, but cannot establish graph membership.
    """

    node_id: NodeId
    input_data: InputT
    dependency_results: Mapping[NodeId, ExecutionResult[object]]

    def __post_init__(self) -> None:
        """Validate references and copy the dependency mapping."""
        _require_node_id(self.node_id)
        if not isinstance(self.dependency_results, Mapping):
            raise WorkflowError("workflow dependency results must be a mapping")
        copied: dict[NodeId, ExecutionResult[object]] = {}
        for node_id, result in self.dependency_results.items():
            _require_node_id(node_id)
            if not isinstance(result, ExecutionResult):
                raise WorkflowError("workflow dependency outcome must be an ExecutionResult")
            copied[node_id] = result
        object.__setattr__(self, "dependency_results", MappingProxyType(copied))

    def dependency_result(self, node_id: NodeId) -> ExecutionResult[object]:
        """Return a visible dependency result using safe lookup diagnostics."""
        _require_node_id(node_id)
        if node_id not in self.dependency_results:
            raise WorkflowError("workflow dependency result is not available in this context")
        return self.dependency_results[node_id]

    def __repr__(self) -> str:
        """Omit identities, inputs, outcomes, and nested payloads."""
        return "WorkflowNodeContext()"


type WorkflowNodeHandler[InputT, OutputT] = Callable[
    [WorkflowNodeContext[InputT]], Awaitable[ExecutionResult[OutputT]]
]


class WorkflowRunState[InputT]:
    """Own retained node outcomes for one run with one coordinator.

    This class does not execute handlers or interpret statuses. It is not a
    concurrent writer API. Inputs, results, and nested metadata are not deep-copied.
    """

    __slots__ = ("_graph", "_input_data", "_results")

    def __init__(self, graph: WorkflowGraph, *, input_data: InputT) -> None:
        """Create an independent empty result store for a validated graph."""
        if not isinstance(graph, WorkflowGraph):
            raise WorkflowError("workflow run requires a WorkflowGraph")
        self._graph = graph
        self._input_data = input_data
        self._results: dict[NodeId, ExecutionResult[object]] = {}

    @property
    def results(self) -> Mapping[NodeId, ExecutionResult[object]]:
        """Return an immutable snapshot, never the live result dictionary."""
        return MappingProxyType(dict(self._results))

    def record_result[OutputT](self, node_id: NodeId, result: ExecutionResult[OutputT]) -> None:
        """Retain the original outcome once without interpreting its status."""
        self._require_member(node_id)
        if not isinstance(result, ExecutionResult):
            raise WorkflowError("workflow node outcome must be an ExecutionResult")
        if node_id in self._results:
            raise WorkflowError("workflow node result has already been recorded")
        # ExecutionResult is invariant to the type checker. This is one-way
        # erasure into read-only heterogeneous storage, never a typed downcast.
        # The original frozen outcome is retained and lookup exposes only object.
        self._results[node_id] = cast("ExecutionResult[object]", result)

    def result_for(self, node_id: NodeId) -> ExecutionResult[object]:
        """Look up a recorded outcome with a safe error for absent results."""
        self._require_member(node_id)
        if node_id not in self._results:
            raise WorkflowError("workflow node result has not been recorded")
        return self._results[node_id]

    def context_for(self, node_id: NodeId) -> WorkflowNodeContext[InputT]:
        """Snapshot exactly the direct dependencies in their declared order.

        All dependency results must exist. Their statuses do not control context
        construction; deciding whether a node may execute belongs to an executor.
        """
        self._require_member(node_id)
        dependencies = self._graph.nodes[node_id].depends_on
        if any(dependency not in self._results for dependency in dependencies):
            raise WorkflowError("workflow direct dependency results are incomplete")
        return WorkflowNodeContext(
            node_id=node_id,
            input_data=self._input_data,
            dependency_results={
                dependency: self._results[dependency] for dependency in dependencies
            },
        )

    def _require_member(self, node_id: NodeId) -> None:
        _require_node_id(node_id)
        if node_id not in self._graph.nodes:
            raise WorkflowError("workflow node reference is not in this graph")

    def __repr__(self) -> str:
        """Omit graph identities, run input, and retained outcomes."""
        return "WorkflowRunState()"
