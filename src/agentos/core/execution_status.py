"""Execution outcome states and status helpers."""

from __future__ import annotations

from enum import StrEnum


class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PARTIAL = "partial"
    RETRY = "retry"

    @property
    def is_success(self) -> bool:
        return self is ExecutionStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT)

    @property
    def is_terminal(self) -> bool:
        return self in (
            ExecutionStatus.SUCCESS,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMEOUT,
        )

    @property
    def should_retry(self) -> bool:
        return self is ExecutionStatus.RETRY
