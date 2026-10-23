"""Tests for the execution status contract."""

from agentos.core import ExecutionStatus


def test_success() -> None:
    """Success status helpers describe a completed successful run."""
    status = ExecutionStatus.SUCCESS
    assert status.is_success
    assert not status.is_failure
    assert status.is_terminal
    assert not status.should_retry


def test_failed() -> None:
    """Failure status helpers describe a completed failed run."""
    status = ExecutionStatus.FAILED
    assert not status.is_success
    assert status.is_failure
    assert status.is_terminal


def test_timeout() -> None:
    """Timeout is both a failure and a terminal status."""
    status = ExecutionStatus.TIMEOUT
    assert status.is_failure
    assert status.is_terminal


def test_retry() -> None:
    """Retry status is retryable and is not terminal failure."""
    status = ExecutionStatus.RETRY
    assert status.should_retry
    assert not status.is_terminal
    assert not status.is_failure


def test_cancelled_and_partial() -> None:
    """Cancellation is terminal while partial completion is nonterminal."""
    assert ExecutionStatus.CANCELLED.is_terminal
    assert not ExecutionStatus.PARTIAL.is_terminal
    assert not ExecutionStatus.PARTIAL.is_success


def test_string_values() -> None:
    """Status values serialize as stable strings."""
    assert ExecutionStatus.SUCCESS.value == "success"
    assert ExecutionStatus("retry") is ExecutionStatus.RETRY
