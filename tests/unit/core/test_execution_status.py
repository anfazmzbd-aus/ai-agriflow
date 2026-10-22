"""Tests for the execution status contract."""

from agentos.core import ExecutionStatus


def test_success() -> None:
    status = ExecutionStatus.SUCCESS
    assert status.is_success
    assert not status.is_failure
    assert status.is_terminal
    assert not status.should_retry


def test_failed() -> None:
    status = ExecutionStatus.FAILED
    assert not status.is_success
    assert status.is_failure
    assert status.is_terminal


def test_timeout() -> None:
    status = ExecutionStatus.TIMEOUT
    assert status.is_failure
    assert status.is_terminal


def test_retry() -> None:
    status = ExecutionStatus.RETRY
    assert status.should_retry
    assert not status.is_terminal
    assert not status.is_failure


def test_cancelled_and_partial() -> None:
    assert ExecutionStatus.CANCELLED.is_terminal
    assert not ExecutionStatus.PARTIAL.is_terminal
    assert not ExecutionStatus.PARTIAL.is_success


def test_string_values() -> None:
    assert ExecutionStatus.SUCCESS.value == "success"
    assert ExecutionStatus("retry") is ExecutionStatus.RETRY
