"""Immutable workflow topology and deterministic dependency ordering."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from heapq import heapify, heappop, heappush
from types import MappingProxyType
from typing import NamedTuple, NewType

from agentos.base.exceptions import WorkflowGraphError

NodeId = NewType("NodeId", str)


@dataclass(frozen=True, slots=True)
class WorkflowNodeSpec:
    """Declare a graph-local node ID and its direct prerequisites."""

    node_id: NodeId
    depends_on: tuple[NodeId, ...] = ()


class WorkflowEdge(NamedTuple):
    """A directed prerequisite-to-dependent edge."""

    prerequisite: NodeId
    dependent: NodeId


@dataclass(frozen=True, slots=True, eq=False, init=False)
class WorkflowGraph:
    """An immutable, validated DAG with declaration-order tie-breaking."""

    nodes: Mapping[NodeId, WorkflowNodeSpec]
    edges: tuple[WorkflowEdge, ...]
    _order: tuple[NodeId, ...]

    def __init__(self, nodes: Sequence[WorkflowNodeSpec]) -> None:
        """Snapshot declarations and reject malformed topology before returning."""
        indexed = _index_nodes(nodes)
        edges = _validate_edges(indexed)
        order = _sort_nodes(indexed, edges)
        object.__setattr__(self, "nodes", MappingProxyType(indexed))
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "_order", order)

    def topological_order(self) -> tuple[NodeId, ...]:
        """Return node IDs with each prerequisite before its dependent."""
        return self._order


def _valid_id(value: object) -> bool:
    """Check identity without calling user-defined string methods."""
    return type(value) is str and bool(value.strip())


def _is_node_sequence(value: object) -> bool:
    return not isinstance(value, (str, bytes, bytearray)) and isinstance(value, Sequence)


def _index_nodes(nodes: Sequence[WorkflowNodeSpec]) -> dict[NodeId, WorkflowNodeSpec]:
    if not _is_node_sequence(nodes):
        msg = "workflow graph nodes must be an ordered sequence of node declarations"
        raise WorkflowGraphError(msg)
    declarations = tuple(nodes)
    if not declarations:
        msg = "workflow graph requires at least one node"
        raise WorkflowGraphError(msg)

    indexed: dict[NodeId, WorkflowNodeSpec] = {}
    for position, node in enumerate(declarations, start=1):
        if type(node) is not WorkflowNodeSpec:
            msg = f"invalid workflow node declaration at position {position}"
            raise WorkflowGraphError(msg)
        if not _valid_id(node.node_id):
            msg = f"workflow node ID at position {position} must be a nonblank string"
            raise WorkflowGraphError(msg)
        if node.node_id in indexed:
            msg = f"duplicate workflow node ID at position {position}"
            raise WorkflowGraphError(msg)
        indexed[node.node_id] = node
    return indexed


def _validate_edges(nodes: Mapping[NodeId, WorkflowNodeSpec]) -> tuple[WorkflowEdge, ...]:
    edges = []
    first_missing: tuple[int, int] | None = None
    for position, node in enumerate(nodes.values(), start=1):
        if type(node.depends_on) is not tuple:
            msg = f"workflow dependencies at node position {position} must be a tuple"
            raise WorkflowGraphError(msg)
        seen: set[NodeId] = set()
        for dependency_position, prerequisite in enumerate(node.depends_on, start=1):
            location = f"node position {position}, dependency position {dependency_position}"
            if not _valid_id(prerequisite):
                msg = f"workflow dependency ID at {location} must be a nonblank string"
                raise WorkflowGraphError(msg)
            if prerequisite in seen:
                msg = f"duplicate workflow dependency at {location}"
                raise WorkflowGraphError(msg)
            if prerequisite == node.node_id:
                msg = f"workflow node cannot depend on itself at {location}"
                raise WorkflowGraphError(msg)
            if prerequisite not in nodes and first_missing is None:
                first_missing = (position, dependency_position)
            seen.add(prerequisite)
            edges.append(WorkflowEdge(prerequisite, node.node_id))

    if first_missing is not None:
        position, dependency_position = first_missing
        msg = (
            f"missing workflow dependency at node position {position}, "
            f"dependency position {dependency_position}"
        )
        raise WorkflowGraphError(msg)
    return tuple(edges)


def _sort_nodes(
    nodes: Mapping[NodeId, WorkflowNodeSpec], edges: tuple[WorkflowEdge, ...]
) -> tuple[NodeId, ...]:
    node_ids = tuple(nodes)
    positions = {node_id: position for position, node_id in enumerate(node_ids)}
    successors: list[list[int]] = [[] for _ in node_ids]
    in_degree = [len(node.depends_on) for node in nodes.values()]

    for prerequisite, dependent in edges:
        successors[positions[prerequisite]].append(positions[dependent])

    ready = [position for position, count in enumerate(in_degree) if count == 0]
    heapify(ready)
    order: list[NodeId] = []
    while ready:
        position = heappop(ready)
        order.append(node_ids[position])
        for successor in successors[position]:
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                heappush(ready, successor)

    if len(order) != len(nodes):
        msg = "workflow graph contains a dependency cycle"
        raise WorkflowGraphError(msg)
    return tuple(order)
