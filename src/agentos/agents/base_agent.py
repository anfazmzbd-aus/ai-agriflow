"""Reusable lifecycle-aware base class for typed asynchronous agents."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from agentos.base.exceptions import AgentError, AgentOSRuntimeError
from agentos.base.lifecycle import LifecycleComponent, LifecycleState


class BaseAgent[InputT, OutputT](LifecycleComponent, ABC):
    """Agent base that validates lifecycle state and normalizes execution errors.

    Subclasses implement ``_execute``. The lifecycle hooks default to no-ops and
    may be overridden by agents that acquire resources. ``run`` requires the
    component to be started, but does not serialize execution against shutdown.
    """

    async def run(self, agent_input: InputT) -> OutputT:
        """Execute one input and return its raw typed result.

        The started-state check is an admission check. A concurrent ``stop`` may
        complete while ``_execute`` is still running.
        """
        if self.lifecycle_state is not LifecycleState.STARTED:
            raise AgentOSRuntimeError(
                f"cannot run agent {self.name!r} from {self.lifecycle_state.value}"
            )

        try:
            return await self._execute(agent_input)
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            raise
        except AgentError:
            raise
        except Exception as exc:
            raise AgentError("agent execution failed") from exc

    async def _initialize(self) -> None:
        """Initialize agent resources; override when setup is required."""

    async def _start(self) -> None:
        """Start agent resources; override when startup work is required."""

    async def _stop(self) -> None:
        """Release agent resources; override when cleanup is required."""

    @abstractmethod
    async def _execute(self, agent_input: InputT) -> OutputT:
        """Implement the agent's domain-specific asynchronous execution."""
