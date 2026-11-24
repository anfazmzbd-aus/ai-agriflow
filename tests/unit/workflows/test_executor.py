"""Preflight, ordering, outcomes, and compatibility of the sequential executor."""

from __future__ import annotations

from collections.abc import Awaitable, Sequence
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from agentos.base import WorkflowError
from agentos.core import ExecutionResult, ExecutionStatus
from agentos.workflows import (
    NodeId,
    SequentialWorkflowExecutor,
    WorkflowGraph,
    WorkflowNodeBinding,
    WorkflowNodeContext,
    WorkflowNodeHandler,
    WorkflowNodeSpec,
)


def topology(*declarations: tuple[str, tuple[str, ...]]) -> WorkflowGraph:
    """Create graph declarations without executing handlers."""
    return WorkflowGraph(
        tuple(
            WorkflowNodeSpec(NodeId(name), tuple(NodeId(dep) for dep in dependencies))
            for name, dependencies in declarations
        )
    )


async def ok(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
    """Return the typed input as an outcome."""
    return ExecutionResult[int].success(context.input_data)


@pytest.mark.parametrize(
    ("declarations", "expected"),
    [
        ((("root", ()),), ("root",)),
        ((("end", ("middle",)), ("middle", ("root",)), ("root", ())), ("root", "middle", "end")),
        (
            (("join", ("right", "left")), ("left", ("root",)), ("right", ("root",)), ("root", ())),
            ("root", "left", "right", "join"),
        ),
        (
            (("consumer", ("database",)), ("metrics", ()), ("database", ()), ("cache", ())),
            ("metrics", "database", "consumer", "cache"),
        ),
    ],
)
async def test_order_context_readiness_and_binding_order(
    declarations: tuple[tuple[str, tuple[str, ...]], ...], expected: tuple[str, ...]
) -> None:
    """Use topology order, not binding order, and expose only successful prerequisites."""
    graph = topology(*declarations)
    calls: list[NodeId] = []
    originals: dict[NodeId, ExecutionResult[int]] = {}

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
        calls.append(context.node_id)
        assert tuple(context.dependency_results) == graph.nodes[context.node_id].depends_on
        assert all(
            result.status is ExecutionStatus.SUCCESS
            for result in context.dependency_results.values()
        )
        assert all(
            context.dependency_result(key) is originals[key] for key in context.dependency_results
        )
        result = ExecutionResult[int].success(context.input_data)
        originals[context.node_id] = result
        return result

    bindings = [
        WorkflowNodeBinding[int](node_id, handler) for node_id in reversed(tuple(graph.nodes))
    ]
    executor = SequentialWorkflowExecutor(graph, bindings)
    bindings.clear()
    outcome = await executor.run(7)
    assert tuple(calls) == expected
    assert outcome.status is ExecutionStatus.SUCCESS
    assert outcome.has_value
    assert outcome.value is not None
    assert tuple(outcome.value) == expected
    assert all(outcome.value[key] is result for key, result in originals.items())
    assert executor.results == outcome.value


@pytest.mark.parametrize(
    "result",
    [
        ExecutionResult[None].success(None),
        ExecutionResult[object].failure("private failure"),
        ExecutionResult[object].timeout("private timeout"),
        ExecutionResult[object].cancelled("private cancel"),
        ExecutionResult[None].partial(None, error="private partial"),
        ExecutionResult[object].retry("private retry"),
    ],
)
async def test_all_statuses_and_global_fail_fast(result: ExecutionResult[object]) -> None:
    """Retain exact outcomes, including None, and stop independent later nodes."""
    graph = topology(("first", ()), ("second", ("first",)), ("independent", ()))
    calls: list[str] = []

    async def handler(context: WorkflowNodeContext[int]) -> ExecutionResult[object]:
        calls.append(context.node_id)
        return result

    executor = SequentialWorkflowExecutor(
        graph, [WorkflowNodeBinding[int](node_id, handler) for node_id in graph.nodes]
    )
    aggregate = await executor.run(0)
    assert aggregate.value is not None
    assert aggregate.value[NodeId("first")] is result
    assert aggregate.value[NodeId("first")].has_value is result.has_value
    if result.status is ExecutionStatus.SUCCESS:
        assert calls == ["first", "second", "independent"]
        assert aggregate.status is ExecutionStatus.SUCCESS
    else:
        assert calls == ["first"]
        assert tuple(aggregate.value) == ("first",)
        assert aggregate.status is ExecutionStatus.PARTIAL
        assert aggregate.error == "workflow execution did not fully succeed"
    assert "private" not in (aggregate.error or "")


async def test_completed_prefix_and_partial_value_retention() -> None:
    """A join is blocked when a prerequisite returns PARTIAL."""
    graph = topology(
        ("root", ()),
        ("left", ("root",)),
        ("right", ("root",)),
        ("join", ("left", "right")),
        ("later", ()),
    )
    calls: list[str] = []
    partial = ExecutionResult[list[int]].partial([1, 2], error="safe partial")

    async def handler(context: WorkflowNodeContext[None]) -> ExecutionResult[object]:
        calls.append(context.node_id)
        if context.node_id == "right":
            return cast("ExecutionResult[object]", partial)
        return ExecutionResult[object].success(context.node_id)

    executor = SequentialWorkflowExecutor(
        graph, [WorkflowNodeBinding[None](key, handler) for key in graph.nodes]
    )
    report = await executor.run(None)
    assert calls == ["root", "left", "right"]
    assert report.status is ExecutionStatus.PARTIAL
    assert executor.results[NodeId("right")] is partial
    assert executor.results[NodeId("right")].value == [1, 2]
    assert NodeId("join") not in executor.results
    assert NodeId("later") not in executor.results


@pytest.mark.parametrize("bad", [None, 1, True, "", " \t\n", object()])
def test_invalid_binding_ids(bad: object) -> None:
    """Reject malformed IDs without formatting them."""
    with pytest.raises(WorkflowError, match="plain nonblank"):
        WorkflowNodeBinding[int](cast("NodeId", bad), ok)


@pytest.mark.parametrize("bad", [None, object(), 3])
def test_noncallable_handlers(bad: object) -> None:
    """Reject noncallables before execution."""
    with pytest.raises(WorkflowError, match="must be callable"):
        WorkflowNodeBinding[int](NodeId("root"), cast("WorkflowNodeHandler[int, int]", bad))


@pytest.mark.parametrize("bad", [None, "root", b"root", bytearray(b"root"), set(), iter(())])
def test_invalid_binding_collections(bad: object) -> None:
    """Reject unordered and nonsequence binding collections."""
    with pytest.raises(WorkflowError, match="ordered sequence"):
        SequentialWorkflowExecutor(
            topology(("root", ())), cast("Sequence[WorkflowNodeBinding[int]]", bad)
        )


def test_preflight_missing_duplicate_extra_and_invalid_bindings() -> None:
    """Preflight the complete binding set before any call."""
    graph = topology(("root", ()), ("leaf", ("root",)))
    root = WorkflowNodeBinding[int](NodeId("root"), ok)
    with pytest.raises(WorkflowError, match="incomplete"):
        SequentialWorkflowExecutor(graph, ())
    with pytest.raises(WorkflowError, match="incomplete"):
        SequentialWorkflowExecutor(graph, [root])
    with pytest.raises(WorkflowError, match=r"duplicate.*position 2"):
        SequentialWorkflowExecutor(graph, [root, root])
    with pytest.raises(WorkflowError, match=r"extra.*position 2"):
        SequentialWorkflowExecutor(graph, [root, WorkflowNodeBinding[int](NodeId("extra"), ok)])
    with pytest.raises(WorkflowError, match=r"invalid.*position 2"):
        SequentialWorkflowExecutor(graph, [root, cast("WorkflowNodeBinding[int]", object())])
    with pytest.raises(WorkflowError, match="WorkflowGraph"):
        SequentialWorkflowExecutor(cast("WorkflowGraph", object()), [])


def test_binding_immutability_and_exact_identity() -> None:
    """Preserve valid identity strings and prevent normal binding mutation."""
    binding = WorkflowNodeBinding[int](NodeId(" A "), ok)
    assert binding.node_id == " A "
    with pytest.raises(FrozenInstanceError):
        binding.__setattr__("_node_id", NodeId("other"))
    SequentialWorkflowExecutor(topology((" A ", ())), [binding])
    with pytest.raises(WorkflowError, match="extra"):
        SequentialWorkflowExecutor(topology(("a", ())), [binding])


async def test_callable_object_and_awaitable_factory_are_supported() -> None:
    """Do not reject valid non-coroutine-function forms during preflight."""

    async def value() -> ExecutionResult[int]:
        return ExecutionResult[int].success(4)

    def factory(context: WorkflowNodeContext[int]) -> Awaitable[ExecutionResult[int]]:
        return value()

    class CallableHandler:
        """Implement a typed async call method."""

        async def __call__(self, context: WorkflowNodeContext[int]) -> ExecutionResult[int]:
            return ExecutionResult[int].success(context.input_data)

    graph = topology(("a", ()), ("b", ("a",)))
    executor = SequentialWorkflowExecutor(
        graph,
        [
            WorkflowNodeBinding[int](NodeId("a"), CallableHandler()),
            WorkflowNodeBinding[int](NodeId("b"), factory),
        ],
    )
    outcome = await executor.run(3)
    assert outcome.value is not None
    assert outcome.value[NodeId("a")].value == 3
    assert outcome.value[NodeId("b")].value == 4


async def test_deep_chain_execution_is_iterative() -> None:
    """Execute beyond the recursion limit without recursive graph traversal."""
    ids = tuple(NodeId(str(i)) for i in range(1500))
    graph = WorkflowGraph(
        tuple(WorkflowNodeSpec(key, (ids[i - 1],) if i else ()) for i, key in enumerate(ids))
    )
    executor = SequentialWorkflowExecutor(graph, [WorkflowNodeBinding[int](key, ok) for key in ids])
    outcome = await executor.run(1)
    assert outcome.status is ExecutionStatus.SUCCESS
    assert len(executor.results) == 1500
