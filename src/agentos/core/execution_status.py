"""Execution outcome states and status helpers."""

from __future__ import annotations

from enum import StrEnum


class ExecutionStatus(StrEnum):
    """Enumerate the possible outcomes of one execution."""

    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PARTIAL = "partial"
    RETRY = "retry"

    @property
    def is_success(self) -> bool:
        """Return whether this status represents successful completion."""
        return self is ExecutionStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Return whether this status represents a failed or timed-out run."""
        return self in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT)

    @property
    def is_terminal(self) -> bool:
        """Return whether this status means execution has stopped."""
        return self in (
            ExecutionStatus.SUCCESS,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMEOUT,
        )

    @property
    def should_retry(self) -> bool:
        """Return whether the execution should be attempted again."""
        return self is ExecutionStatus.RETRY
