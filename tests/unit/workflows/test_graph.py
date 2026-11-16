from __future__ import annotations

from collections.abc import MutableMapping, Sequence
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from agentos.base import AgentOSError, WorkflowError, WorkflowGraphError
from agentos.workflows import NodeId, WorkflowEdge, WorkflowGraph, WorkflowNodeSpec


def _node(name: str, *dependencies: str) -> WorkflowNodeSpec:
    return WorkflowNodeSpec(NodeId(name), tuple(map(NodeId, dependencies)))


def test_singleton() -> None:
    """Expose one node and an empty edge tuple."""
    only = _node("only")
    graph = WorkflowGraph((only,))
    assert tuple(graph.nodes) == (only.node_id,)
    assert graph.nodes[only.node_id] == only
    assert graph.edges == ()
    assert graph.topological_order() == (only.node_id,)


def test_diamond_with_forward_references_and_disconnected_nodes() -> None:
    """Sort all components and retain the declared order of derived edges."""
    nodes = (
        _node("join", "left", "right"),
        _node("right", "root"),
        _node("left", "root"),
        _node("root"),
        _node("isolated"),
        _node("other-leaf", "other-root"),
        _node("other-root"),
    )
    graph = WorkflowGraph(nodes)
    assert tuple(graph.nodes) == tuple(node.node_id for node in nodes)
    assert graph.edges == (
        WorkflowEdge(NodeId("left"), NodeId("join")),
        WorkflowEdge(NodeId("right"), NodeId("join")),
        WorkflowEdge(NodeId("root"), NodeId("right")),
        WorkflowEdge(NodeId("root"), NodeId("left")),
        WorkflowEdge(NodeId("other-root"), NodeId("other-leaf")),
    )
    expected = ("root", "right", "left", "join", "isolated", "other-root", "other-leaf")
    actual = graph.topological_order()
    assert actual == expected
    assert graph.topological_order() == actual
    assert WorkflowGraph(list(nodes)).topological_order() == actual
    reversed_join = (_node("join", "right", "left"), *nodes[1:])
    assert WorkflowGraph(reversed_join).topological_order() == actual


def test_exact_and_case_sensitive_identity() -> None:
    """Preserve IDs as supplied and use ordinary mapping lookup."""
    graph = WorkflowGraph((_node(" a "), _node("A"), _node("a", " a ")))
    assert graph.topological_order() == (" a ", "A", "a")
    assert graph.nodes[NodeId("a")].depends_on == (" a ",)
    with pytest.raises(KeyError):
        _ = graph.nodes[NodeId("missing")]


@pytest.mark.parametrize(
    ("declarations", "message"),
    [
        (None, "ordered sequence"),
        ("node", "ordered sequence"),
        (b"node", "ordered sequence"),
        (bytearray(b"node"), "ordered sequence"),
        ({_node("a")}, "ordered sequence"),
        ((), "at least one node"),
        ((object(),), "invalid workflow node declaration at position 1"),
        ((WorkflowNodeSpec(cast("NodeId", 1)),), "node ID at position 1"),
        ((_node(""),), "node ID at position 1"),
        ((_node(" \t\n"),), "node ID at position 1"),
        ((_node("a"), _node("a", "b")), "duplicate workflow node ID at position 2"),
        (
            (WorkflowNodeSpec(NodeId("a"), cast("tuple[NodeId, ...]", ["b"])),),
            "dependencies at node position 1 must be a tuple",
        ),
        (
            (WorkflowNodeSpec(NodeId("a"), (cast("NodeId", 1),)),),
            "dependency ID at node position 1, dependency position 1",
        ),
        ((_node("a", " "),), "dependency ID at node position 1, dependency position 1"),
        (
            (_node("a", "b", "b"), _node("b")),
            "duplicate workflow dependency at node position 1, dependency position 2",
        ),
        ((_node("a", "a"),), "cannot depend on itself"),
        (
            (_node("a", "b", "missing"), _node("b")),
            "missing workflow dependency at node position 1, dependency position 2",
        ),
    ],
)
def test_invalid_declarations(declarations: object, message: str) -> None:
    """Reject malformed runtime input using the public graph exception."""
    with pytest.raises(WorkflowGraphError, match=message):
        WorkflowGraph(cast("Sequence[WorkflowNodeSpec]", declarations))


def test_validation_precedence() -> None:
    """Check node IDs before dependencies, and edge shape before missing IDs."""
    with pytest.raises(WorkflowGraphError, match="duplicate workflow node ID at position 2"):
        WorkflowGraph((_node("a", ""), _node("a")))
    with pytest.raises(WorkflowGraphError, match="duplicate workflow dependency"):
        WorkflowGraph((_node("a", "missing"), _node("b", "c", "c"), _node("c")))
    with pytest.raises(WorkflowGraphError, match="missing workflow dependency"):
        WorkflowGraph((_node("a", "b"), _node("b", "a"), _node("c", "missing")))


@pytest.mark.parametrize(
    "declarations",
    [
        (_node("a", "b"), _node("b", "a")),
        (_node("a", "c"), _node("b", "a"), _node("c", "b")),
        (_node("independent"), _node("downstream", "a"), _node("a", "b"), _node("b", "a")),
    ],
)
def test_cycles(declarations: tuple[WorkflowNodeSpec, ...]) -> None:
    """Reject cycles even when some nodes can be sorted."""
    with pytest.raises(WorkflowGraphError, match="dependency cycle"):
        WorkflowGraph(declarations)


def test_deep_graphs_use_iterative_validation() -> None:
    """Handle long chains and cycles beyond the usual recursion limit."""
    ids = tuple(NodeId(str(i)) for i in range(2_000))
    chain = [WorkflowNodeSpec(node_id, (ids[i - 1],) if i else ()) for i, node_id in enumerate(ids)]
    assert WorkflowGraph(chain[::-1]).topological_order() == ids
    chain[0] = WorkflowNodeSpec(ids[0], (ids[-1],))
    with pytest.raises(WorkflowGraphError, match="dependency cycle"):
        WorkflowGraph(chain)


def test_graph_owns_immutable_topology() -> None:
    """Keep the graph independent from mutations of the input list."""
    declarations = [_node("root"), _node("leaf", "root")]
    graph = WorkflowGraph(declarations)
    declarations.clear()

    root = NodeId("root")
    leaf = NodeId("leaf")
    assert graph.topological_order() == (root, leaf)
    assert graph.edges == (WorkflowEdge(root, leaf),)
    nodes = cast("MutableMapping[NodeId, WorkflowNodeSpec]", graph.nodes)
    with pytest.raises(TypeError):
        nodes[root] = _node("replacement")
    with pytest.raises(FrozenInstanceError):
        graph.nodes[leaf].__setattr__("depends_on", ())
    with pytest.raises(FrozenInstanceError):
        graph.__setattr__("edges", ())
    with pytest.raises(AttributeError):
        graph.edges[0].__setattr__("dependent", root)


def test_errors_use_existing_hierarchy_and_hide_raw_identifiers() -> None:
    """Keep diagnostics positional and free of untrusted identifier text."""
    with pytest.raises(WorkflowGraphError) as raised:
        WorkflowGraph((_node("secret\nnode", "secret\x1bdependency"),))
    assert isinstance(raised.value, WorkflowError)
    assert isinstance(raised.value, AgentOSError)
    assert str(raised.value) == (
        "missing workflow dependency at node position 1, dependency position 1"
    )
