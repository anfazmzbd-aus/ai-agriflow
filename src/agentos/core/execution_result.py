"""Typed results returned by AgentOS execution components."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from agentos.core.execution_status import ExecutionStatus


@dataclass(frozen=True, slots=True)
class ExecutionResult[T]:
    """Outcome, optional value, error message, and metadata for one execution.

    ``has_value`` distinguishes a missing value from a successful ``None`` value.
    Metadata is copied into a read-only mapping when the result is created.
    """

    status: ExecutionStatus
    value: T | None = None
    error: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
    has_value: bool = False

    def __post_init__(self) -> None:
        """Copy metadata and enforce status-specific result invariants."""
        if not isinstance(self.status, ExecutionStatus):
            raise TypeError("status must be an ExecutionStatus")
        if not isinstance(self.has_value, bool):
            raise TypeError("has_value must be a bool")
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("error must be a string")
        if not self.has_value and self.value is not None:
            raise ValueError("value cannot be set when has_value is false")
        if self.error is not None and not self.error.strip():
            raise ValueError("error must be a non-empty string when provided")

        if self.status is ExecutionStatus.SUCCESS:
            if not self.has_value:
                raise ValueError("successful results must have a value")
            if self.error is not None:
                raise ValueError("successful results cannot have an error")
        elif self.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT):
            if self.has_value:
                raise ValueError("failed results cannot have a value")
            if self.error is None:
                raise ValueError("failed and timeout results require an error")
        elif self.status is ExecutionStatus.PARTIAL:
            if not self.has_value:
                raise ValueError("partial results must have a value")
        elif self.status in (ExecutionStatus.CANCELLED, ExecutionStatus.RETRY):
            if self.has_value:
                raise ValueError("cancelled and retry results cannot have a value")

        try:
            copied_metadata = dict(self.metadata)
        except (TypeError, ValueError) as exc:
            raise TypeError("metadata must be a mapping of string keys to values") from exc
        if any(not isinstance(key, str) for key in copied_metadata):
            raise TypeError("metadata keys must be strings")
        object.__setattr__(self, "metadata", MappingProxyType(copied_metadata))

    @classmethod
    def success(
        cls,
        value: T,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionResult[T]:
        """Create a successful result, including when ``value`` is ``None``."""
        return cls(
            status=ExecutionStatus.SUCCESS,
            value=value,
            has_value=True,
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def failure(
        cls,
        error: str,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionResult[T]:
        """Create a failed result with a required explanatory message."""
        return cls(
            status=ExecutionStatus.FAILED,
            error=error,
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def timeout(
        cls,
        error: str,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionResult[T]:
        """Create a timed-out result with a required explanatory message."""
        return cls(
            status=ExecutionStatus.TIMEOUT,
            error=error,
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def partial(
        cls,
        value: T,
        *,
        error: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionResult[T]:
        """Create a partial result with an available value and optional detail."""
        return cls(
            status=ExecutionStatus.PARTIAL,
            value=value,
            has_value=True,
            error=error,
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def retry(
        cls,
        error: str | None = None,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionResult[T]:
        """Create a retryable result, optionally describing why it should retry."""
        return cls(
            status=ExecutionStatus.RETRY,
            error=error,
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def cancelled(
        cls,
        error: str | None = None,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> ExecutionResult[T]:
        """Create a cancelled result with optional explanatory detail."""
        return cls(
            status=ExecutionStatus.CANCELLED,
            error=error,
            metadata={} if metadata is None else metadata,
        )
