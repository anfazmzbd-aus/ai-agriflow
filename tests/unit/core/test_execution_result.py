"""Tests for the generic execution result contract."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from agentos.core import ExecutionResult, ExecutionStatus


def test_success_result_preserves_value_and_status() -> None:
    """Success results retain their typed value and status helpers."""
    result = ExecutionResult[int].success(42)

    assert result.status is ExecutionStatus.SUCCESS
    assert result.value == 42
    assert result.has_value
    assert result.error is None
    assert result.status.is_success


def test_none_value_is_distinct_from_missing_value() -> None:
    """An explicit None can be a successful result value."""
    result = ExecutionResult[None].success(None)

    assert result.value is None
    assert result.has_value


def test_failure_timeout_partial_retry_and_cancelled_factories() -> None:
    """Factories assign expected statuses and carry optional values or errors."""
    failure = ExecutionResult[str].failure("invalid input")
    timeout = ExecutionResult[str].timeout("deadline exceeded")
    partial = ExecutionResult[str].partial("some output", error="step failed")
    retry = ExecutionResult[str].retry("temporary issue")
    cancelled = ExecutionResult[str].cancelled()

    assert failure.status is ExecutionStatus.FAILED
    assert failure.error == "invalid input"
    assert timeout.status is ExecutionStatus.TIMEOUT
    assert timeout.status.is_failure
    assert partial.status is ExecutionStatus.PARTIAL
    assert partial.value == "some output"
    assert partial.error == "step failed"
    assert retry.status is ExecutionStatus.RETRY
    assert retry.status.should_retry
    assert retry.error == "temporary issue"
    assert cancelled.status is ExecutionStatus.CANCELLED
    assert cancelled.error is None


def test_metadata_is_copied_and_read_only() -> None:
    """Results own a copy of metadata and expose it as a read-only mapping."""
    metadata: dict[str, object] = {"attempt": 1}
    result = ExecutionResult[int].success(1, metadata=metadata)
    metadata["attempt"] = 2

    assert result.metadata == {"attempt": 1}
    with pytest.raises(TypeError):
        result.metadata["attempt"] = 3  # type: ignore[index]


def test_metadata_default_is_independent_per_result() -> None:
    """Default metadata is not shared between result instances."""
    first = ExecutionResult[int].success(1)
    second = ExecutionResult[int].success(2)

    assert first.metadata == second.metadata == {}
    assert first.metadata is not second.metadata


@pytest.mark.parametrize(
    ("status", "value", "error", "has_value"),
    [
        (ExecutionStatus.SUCCESS, None, None, False),
        (ExecutionStatus.SUCCESS, 1, "conflicting", True),
        (ExecutionStatus.FAILED, None, None, False),
        (ExecutionStatus.FAILED, 1, "conflicting", True),
        (ExecutionStatus.TIMEOUT, None, "   ", False),
        (ExecutionStatus.PARTIAL, None, None, False),
        (ExecutionStatus.RETRY, 1, None, True),
        (ExecutionStatus.CANCELLED, 1, None, True),
        (ExecutionStatus.SUCCESS, 1, None, False),
    ],
)
def test_invalid_status_value_error_combinations_are_rejected(
    status: ExecutionStatus,
    value: int | None,
    error: str | None,
    has_value: bool,
) -> None:
    """Invalid or contradictory result states fail at construction."""
    with pytest.raises(
        ValueError, match=r"value|successful|failed|non-empty|partial|retry|cancelled"
    ):
        ExecutionResult[int](status, value, error, has_value=has_value)


def test_empty_error_and_non_string_metadata_key_are_rejected() -> None:
    """Error messages and metadata keys are validated at the boundary."""
    with pytest.raises(ValueError, match="non-empty"):
        ExecutionResult[int].failure("  ")

    invalid_metadata: Mapping[str, object] = {1: "invalid"}  # type: ignore[dict-item]
    with pytest.raises(TypeError, match="keys must be strings"):
        ExecutionResult[int].success(1, metadata=invalid_metadata)

    with pytest.raises(TypeError, match="error must be a string"):
        ExecutionResult[int](ExecutionStatus.RETRY, error=1)  # type: ignore[arg-type]


def test_direct_construction_requires_execution_status() -> None:
    """Direct construction rejects strings in place of the public enum."""
    with pytest.raises(TypeError, match="ExecutionStatus"):
        ExecutionResult[int]("success", 1, has_value=True)  # type: ignore[arg-type]
