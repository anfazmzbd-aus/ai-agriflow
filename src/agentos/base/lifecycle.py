"""Asynchronous lifecycle contract for opt-in AgentOS components."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import StrEnum

from agentos.base.component import BaseComponent
from agentos.base.exceptions import AgentOSRuntimeError


class LifecycleState(StrEnum):
    """Lifecycle state of a component that opts into lifecycle management."""

    NEW = "new"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    FAILED = "failed"


class LifecycleComponent(BaseComponent, ABC):
    """BaseComponent with serialized asynchronous lifecycle transitions.

    Subclasses implement the three hooks. Hooks must not call the public lifecycle
    methods recursively. A failed or cancelled hook leaves the component FAILED;
    callers may then retry cleanup with ``stop()``.
    """

    def __init__(self, name: str) -> None:
        """Initialize component identity and a fresh lifecycle state/lock."""
        super().__init__(name)
        self._lifecycle_state = LifecycleState.NEW
        self._lifecycle_lock = asyncio.Lock()
        self._lifecycle_owner: asyncio.Task[object] | None = None

    @property
    def lifecycle_state(self) -> LifecycleState:
        """Return the current lifecycle state without permitting assignment."""
        return self._lifecycle_state

    async def initialize(self) -> None:
        """Initialize resources; repeated calls while initialized are no-ops."""
        async with self._transition_lock():
            if self._lifecycle_state is LifecycleState.INITIALIZED:
                return
            if self._lifecycle_state is not LifecycleState.NEW:
                raise self._invalid_transition("initialize")
            await self._invoke_hook(self._initialize)
            self._lifecycle_state = LifecycleState.INITIALIZED

    async def start(self) -> None:
        """Start an initialized component; repeated calls while started are no-ops."""
        async with self._transition_lock():
            if self._lifecycle_state is LifecycleState.STARTED:
                return
            if self._lifecycle_state is not LifecycleState.INITIALIZED:
                raise self._invalid_transition("start")
            await self._invoke_hook(self._start)
            self._lifecycle_state = LifecycleState.STARTED

    async def stop(self) -> None:
        """Stop the component or retry cleanup after a failed lifecycle hook."""
        async with self._transition_lock():
            if self._lifecycle_state is LifecycleState.STOPPED:
                return
            if self._lifecycle_state is LifecycleState.NEW:
                self._lifecycle_state = LifecycleState.STOPPED
                return
            if self._lifecycle_state not in (
                LifecycleState.INITIALIZED,
                LifecycleState.STARTED,
                LifecycleState.FAILED,
            ):
                raise self._invalid_transition("stop")
            await self._invoke_hook(self._stop)
            self._lifecycle_state = LifecycleState.STOPPED

    @abstractmethod
    async def _initialize(self) -> None:
        """Acquire or prepare resources needed before the component can start."""

    @abstractmethod
    async def _start(self) -> None:
        """Make an initialized component ready to perform its work."""

    @abstractmethod
    async def _stop(self) -> None:
        """Release resources, including any resources acquired before a failure."""

    def _transition_lock(self) -> asyncio.Lock:
        """Return the transition lock, rejecting same-task recursive calls."""
        current_task = asyncio.current_task()
        if current_task is not None and current_task is self._lifecycle_owner:
            raise AgentOSRuntimeError("lifecycle methods cannot be called recursively")
        return self._lifecycle_lock

    async def _invoke_hook(self, hook: _LifecycleHook) -> None:
        """Run a hook and mark the component failed if it raises or is cancelled."""
        self._lifecycle_owner = asyncio.current_task()
        try:
            await hook()
        except asyncio.CancelledError:
            self._lifecycle_state = LifecycleState.FAILED
            raise
        except Exception:
            self._lifecycle_state = LifecycleState.FAILED
            raise
        finally:
            self._lifecycle_owner = None

    def _invalid_transition(self, operation: str) -> AgentOSRuntimeError:
        """Build an error describing an unsupported lifecycle operation."""
        return AgentOSRuntimeError(
            f"cannot {operation} component {self.name!r} from {self._lifecycle_state.value}"
        )


_LifecycleHook = Callable[[], Awaitable[None]]
