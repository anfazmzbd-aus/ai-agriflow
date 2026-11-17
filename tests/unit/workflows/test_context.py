"""Ownership, visibility, and diagnostics for DAG contexts."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from agentos.base import AgentOSError, WorkflowError
from agentos.core import ExecutionResult, ExecutionStatus
from agentos.workflows import (
    NodeId,
    WorkflowGraph,
    WorkflowNodeContext,
    WorkflowNodeSpec,
    WorkflowRunState,
)

ROOT = NodeId("root")
LEFT = NodeId("left")
RIGHT = NodeId("right")
JOIN = NodeId("join")
OTHER = NodeId("other")


def graph() -> WorkflowGraph:
    """Create a diamond with a disconnected node and reversed join dependencies."""
    return WorkflowGraph(
        (
            WorkflowNodeSpec(ROOT),
            WorkflowNodeSpec(LEFT, (ROOT,)),
            WorkflowNodeSpec(RIGHT, (ROOT,)),
            WorkflowNodeSpec(JOIN, (RIGHT, LEFT)),
            WorkflowNodeSpec(OTHER),
        )
    )


def test_independent_runs_share_only_graph_and_explicit_input() -> None:
    """Stores are independent even when graph and caller input are shared."""
    topology = graph()
    input_data: dict[str, object] = {"nested": []}
    first = WorkflowRunState(topology, input_data=input_data)
    second = WorkflowRunState(topology, input_data=input_data)
    outcome = ExecutionResult[None].success(None)
    first.record_result(ROOT, outcome)
    assert first.result_for(ROOT) is outcome
    assert second.results == {}
    assert first.context_for(ROOT).input_data is input_data
    assert second.context_for(ROOT).input_data is input_data
    assert first.results is not second.results


def test_direct_dependency_visibility_order_and_heterogeneous_identity() -> None:
    """Joins see only direct dependencies, in declared prerequisite order."""
    run = WorkflowRunState(graph(), input_data=None)
    root = ExecutionResult[str].success("root")
    left = ExecutionResult[int].success(7)
    right = ExecutionResult[None].success(None)
    run.record_result(ROOT, root)
    run.record_result(LEFT, left)
    run.record_result(RIGHT, right)
    run.record_result(OTHER, ExecutionResult[str].success("private"))
    context = run.context_for(JOIN)
    assert tuple(context.dependency_results) == (RIGHT, LEFT)
    assert context.dependency_result(LEFT) is left
    assert context.dependency_result(RIGHT) is right
    assert context.dependency_result(RIGHT).has_value
    assert context.node_id == JOIN
    assert context.input_data is None
    assert ROOT not in context.dependency_results
    assert OTHER not in context.dependency_results
    assert run.context_for(ROOT).dependency_results == {}
    with pytest.raises(WorkflowError, match="not available"):
        context.dependency_result(ROOT)
    assert not hasattr(context, "record_result")


@pytest.mark.parametrize(
    "outcome",
    [
        ExecutionResult[None].success(None),
        ExecutionResult[object].failure("safe failure"),
        ExecutionResult[str].partial("partial", error="safe partial"),
        ExecutionResult[object].retry("safe retry"),
        ExecutionResult[object].timeout("safe timeout"),
        ExecutionResult[object].cancelled(),
    ],
)
def test_all_statuses_are_retained_without_scheduling(outcome: ExecutionResult[object]) -> None:
    """A complete dependency result permits a view regardless of its status."""
    run = WorkflowRunState(graph(), input_data="input")
    run.record_result(ROOT, outcome)
    assert run.result_for(ROOT) is outcome
    assert run.context_for(LEFT).dependency_result(ROOT) is outcome
    assert run.results[ROOT].status is outcome.status
    assert run.results[ROOT].has_value is outcome.has_value


def test_snapshot_stability_and_public_immutability() -> None:
    """Old snapshots remain empty and callers cannot write through public views."""
    run = WorkflowRunState(graph(), input_data=None)
    before = run.results
    outcome = ExecutionResult[int].success(1)
    run.record_result(ROOT, outcome)
    after = run.results
    run.record_result(OTHER, ExecutionResult[int].success(2))
    assert before == {}
    assert tuple(after) == (ROOT,)
    assert after[ROOT] is outcome
    with pytest.raises(TypeError):
        cast("MutableMapping[NodeId, ExecutionResult[object]]", after)[ROOT] = outcome
    with pytest.raises(AttributeError):
        run.__setattr__("results", {})
    context = run.context_for(LEFT)
    with pytest.raises(TypeError):
        cast("MutableMapping[NodeId, ExecutionResult[object]]", context.dependency_results)[
            ROOT
        ] = outcome
    with pytest.raises(FrozenInstanceError):
        context.__setattr__("input_data", "replacement")


def test_direct_context_defensively_copies_mapping_but_not_payloads() -> None:
    """Payload sharing is explicit; structural immutability is shallow."""
    nested: list[int] = []
    input_data: dict[str, object] = {"nested": nested}
    outcome = ExecutionResult[list[int]].success(nested, metadata={"nested": nested})
    results: dict[NodeId, ExecutionResult[object]] = {ROOT: outcome}
    context = WorkflowNodeContext(LEFT, input_data, results)
    results.clear()
    nested.append(9)
    assert context.dependency_result(ROOT) is outcome
    assert context.input_data is input_data
    assert outcome.value is nested
    assert outcome.metadata["nested"] is nested
    assert context.input_data["nested"] == [9]


def test_missing_duplicate_and_unknown_outcomes() -> None:
    """Invalid operations leave the store unchanged."""
    run = WorkflowRunState(graph(), input_data=None)
    with pytest.raises(WorkflowError, match="not been recorded"):
        run.result_for(ROOT)
    with pytest.raises(WorkflowError, match="incomplete"):
        run.context_for(JOIN)
    run.record_result(RIGHT, ExecutionResult[int].success(1))
    with pytest.raises(WorkflowError, match="incomplete"):
        run.context_for(JOIN)
    outcome = ExecutionResult[int].success(2)
    run.record_result(ROOT, outcome)
    with pytest.raises(WorkflowError, match="already been recorded"):
        run.record_result(ROOT, ExecutionResult[int].success(3))
    assert run.result_for(ROOT) is outcome
    for operation in (run.context_for, run.result_for):
        with pytest.raises(WorkflowError, match="not in this graph"):
            operation(NodeId("unknown"))
    with pytest.raises(WorkflowError, match="not in this graph"):
        run.record_result(NodeId("unknown"), outcome)


@pytest.mark.parametrize("bad", [None, 1, True, "", " \t\n", object()])
def test_malformed_references_fail_safely(bad: object) -> None:
    """Every reference-taking boundary rejects malformed IDs."""
    node_id = cast("NodeId", bad)
    run = WorkflowRunState(graph(), input_data=None)
    context = run.context_for(ROOT)
    for operation in (run.context_for, run.result_for, context.dependency_result):
        with pytest.raises(WorkflowError, match="plain nonblank string"):
            operation(node_id)
    with pytest.raises(WorkflowError, match="plain nonblank string"):
        run.record_result(node_id, ExecutionResult[int].success(1))
    with pytest.raises(WorkflowError, match="plain nonblank string"):
        WorkflowNodeContext(node_id, None, {})
    with pytest.raises(WorkflowError, match="plain nonblank string"):
        WorkflowNodeContext(ROOT, None, {node_id: ExecutionResult[int].success(1)})


def test_invalid_shapes_and_results() -> None:
    """Malformed objects use the existing workflow exception hierarchy."""
    with pytest.raises(WorkflowError, match="WorkflowGraph"):
        WorkflowRunState(cast("WorkflowGraph", object()), input_data=None)
    run = WorkflowRunState(graph(), input_data=None)
    with pytest.raises(WorkflowError, match="ExecutionResult"):
        run.record_result(ROOT, cast("ExecutionResult[object]", object()))
    with pytest.raises(WorkflowError, match="must be a mapping"):
        WorkflowNodeContext(ROOT, None, cast("Mapping[NodeId, ExecutionResult[object]]", []))
    with pytest.raises(WorkflowError, match="ExecutionResult"):
        WorkflowNodeContext(ROOT, None, {LEFT: cast("ExecutionResult[object]", object())})
    assert run.results == {}


class Sensitive:
    """Fail if diagnostics try to inspect a payload."""

    def __repr__(self) -> str:
        """Reject accidental representation."""
        raise AssertionError("payload representation was invoked")

    def __str__(self) -> str:
        """Reject accidental string conversion."""
        raise AssertionError("payload string conversion was invoked")


class StringSubclass(str):
    """Exercise exact plain-string reference validation."""


def test_private_diagnostics_and_representations() -> None:
    """Never include raw IDs, values, metadata, or unsafe representations."""
    secret = NodeId("secret\n\x1bnode")
    run = WorkflowRunState(WorkflowGraph((WorkflowNodeSpec(secret),)), input_data=Sensitive())
    outcome = ExecutionResult[Sensitive].success(Sensitive(), metadata={"secret": Sensitive()})
    run.record_result(secret, outcome)
    context = WorkflowNodeContext(secret, Sensitive(), {secret: outcome})
    assert repr(run) == "WorkflowRunState()"
    assert repr(context) == "WorkflowNodeContext()"
    with pytest.raises(WorkflowError) as captured:
        run.record_result(secret, outcome)
    assert isinstance(captured.value, AgentOSError)
    assert str(captured.value) == "workflow node result has already been recorded"
    for bad in (Sensitive(), StringSubclass("root")):
        with pytest.raises(WorkflowError, match="plain nonblank string"):
            run.result_for(cast("NodeId", bad))
    with pytest.raises(WorkflowError) as unavailable:
        context.dependency_result(NodeId("secret-other"))
    assert "secret" not in str(unavailable.value)


def test_graph_topology_and_status_helpers_are_unchanged() -> None:
    """Context construction neither changes topology nor reinterprets status helpers."""
    topology = graph()
    original = topology.topological_order()
    run = WorkflowRunState(topology, input_data=None)
    run.record_result(ROOT, ExecutionResult[object].retry())
    run.context_for(LEFT)
    assert topology.topological_order() == original
    assert not ExecutionStatus.RETRY.is_terminal
    assert not ExecutionStatus.PARTIAL.is_terminal
