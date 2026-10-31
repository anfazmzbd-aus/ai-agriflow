from __future__ import annotations

import asyncio
from typing import cast

import pytest

from agentos.agents import Agent, AgentContext, AgentResult, BaseAgent, EchoAgent
from agentos.base import AgentError, AgentOSRuntimeError, LifecycleState


async def test_echo_agent_returns_goal() -> None:
    """EchoAgent should return the requested goal."""
    agent = EchoAgent()

    result = await agent.run(AgentContext(goal="inspect field"))

    assert result.content == "inspect field"
    assert result.metadata["agent"] == "echo"


class IntegerAgent(BaseAgent[int, str]):
    """Concrete typed agent used to exercise BaseAgent behavior."""

    def __init__(self) -> None:
        """Initialize the named test agent and execution observation list."""
        super().__init__("integer-agent")
        self.inputs: list[int] = []

    async def _execute(self, agent_input: int) -> str:
        """Return a typed string result for an integer input."""
        self.inputs.append(agent_input)
        return f"value={agent_input}"


class BlockingIntegerAgent(IntegerAgent):
    """Integer agent with deterministic controls for in-flight execution."""

    def __init__(self) -> None:
        """Create synchronization events used by async behavior tests."""
        super().__init__()
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def _execute(self, agent_input: int) -> str:
        """Signal admission and wait for the test to release execution."""
        self.entered.set()
        await self.release.wait()
        return str(agent_input)


class ContextAgent(BaseAgent[AgentContext, AgentResult]):
    """BaseAgent specialization that matches the existing Agent protocol."""

    def __init__(self, name: str = "context-agent") -> None:
        """Initialize the context/result agent with a stable name."""
        super().__init__(name)

    async def _execute(self, agent_input: AgentContext) -> AgentResult:
        """Convert the context goal to the established result type."""
        return AgentResult(content=agent_input.goal, metadata={"agent": self.name})


async def start[InputT, OutputT](agent: BaseAgent[InputT, OutputT]) -> None:
    """Initialize and start an agent before execution tests."""
    await agent.initialize()
    await agent.start()


@pytest.mark.asyncio
async def test_generic_input_and_output_and_successful_run() -> None:
    """BaseAgent preserves concrete input/output types and returns raw output."""
    agent = IntegerAgent()
    await start(agent)

    result: str = await agent.run(17)

    assert result == "value=17"
    assert agent.inputs == [17]
    assert agent.lifecycle_state is LifecycleState.STARTED


@pytest.mark.asyncio
async def test_run_rejects_before_start_after_stop_and_when_failed() -> None:
    """Lifecycle admission failures remain runtime errors, outside wrapping."""
    new_agent = IntegerAgent()
    with pytest.raises(AgentOSRuntimeError, match="from new"):
        await new_agent.run(1)
    assert new_agent.lifecycle_state is LifecycleState.NEW

    stopped_agent = IntegerAgent()
    await start(stopped_agent)
    await stopped_agent.stop()
    with pytest.raises(AgentOSRuntimeError, match="from stopped"):
        await stopped_agent.run(1)

    failed_agent = FailedInitializationAgent()
    with pytest.raises(RuntimeError, match="initialization failed"):
        await failed_agent.initialize()
    assert failed_agent.lifecycle_state is LifecycleState.FAILED
    with pytest.raises(AgentOSRuntimeError, match="from failed"):
        await failed_agent.run(1)


class FailedInitializationAgent(IntegerAgent):
    """Agent whose initialization fails to exercise the FAILED gate."""

    async def _initialize(self) -> None:
        """Fail startup before the agent can run."""
        raise RuntimeError("initialization failed")


@pytest.mark.asyncio
async def test_default_lifecycle_hooks_are_no_ops() -> None:
    """Simple agents need only implement execution to use lifecycle methods."""
    agent = IntegerAgent()

    await agent.initialize()
    await agent.start()
    assert await agent.run(3) == "value=3"
    await agent.stop()

    assert agent.lifecycle_state is LifecycleState.STOPPED


class CustomLifecycleAgent(IntegerAgent):
    """Agent that records overridable resource lifecycle hooks."""

    def __init__(self) -> None:
        """Create hook observations."""
        super().__init__()
        self.hooks: list[str] = []

    async def _initialize(self) -> None:
        """Record initialization."""
        self.hooks.append("initialize")

    async def _start(self) -> None:
        """Record startup."""
        self.hooks.append("start")

    async def _stop(self) -> None:
        """Record cleanup."""
        self.hooks.append("stop")


@pytest.mark.asyncio
async def test_custom_lifecycle_hooks_are_called_in_order() -> None:
    """Resource-owning subclasses can override the default no-op hooks."""
    agent = CustomLifecycleAgent()

    await agent.initialize()
    await agent.start()
    await agent.stop()

    assert agent.hooks == ["initialize", "start", "stop"]


class AgentErrorProbe(BaseAgent[None, None]):
    """Agent that raises one preconstructed AgentError instance."""

    def __init__(self, error: AgentError) -> None:
        """Store the error to verify identity and traceback behavior."""
        super().__init__("agent-error-probe")
        self.error = error

    async def _execute(self, agent_input: None) -> None:
        """Raise the preconstructed domain error."""
        raise self.error


@pytest.mark.asyncio
async def test_agent_error_propagates_by_identity_with_traceback() -> None:
    """Existing AgentError instances are not wrapped or replaced."""
    expected = AgentError("domain failure")
    agent = AgentErrorProbe(expected)
    await start(agent)

    with pytest.raises(AgentError) as captured:
        await agent.run(None)

    assert captured.value is expected
    assert captured.value.__cause__ is None
    traceback = captured.value.__traceback__
    frames: list[str] = []
    while traceback is not None:
        frames.append(traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    assert "_execute" in frames
    assert agent.lifecycle_state is LifecycleState.STARTED


class UnexpectedErrorAgent(BaseAgent[None, None]):
    """Agent that raises an ordinary error containing a secret-like message."""

    def __init__(self, error: Exception) -> None:
        """Store the original execution failure."""
        super().__init__("safe-agent")
        self.error = error
        self.calls = 0

    async def _execute(self, agent_input: None) -> None:
        """Raise the stored error exactly once per invocation."""
        self.calls += 1
        raise self.error


@pytest.mark.asyncio
async def test_unexpected_error_is_safely_wrapped_and_chained_without_retry() -> None:
    """Generic AgentError text excludes details while cause preserves diagnosis."""
    original = ValueError("token=secret-value")
    agent = UnexpectedErrorAgent(original)
    await start(agent)

    with pytest.raises(AgentError, match="agent execution failed") as captured:
        await agent.run(None)

    assert captured.value.__cause__ is original
    assert "secret-value" not in str(captured.value)
    assert agent.calls == 1
    assert agent.lifecycle_state is LifecycleState.STARTED


@pytest.mark.asyncio
async def test_cancellation_propagates_and_does_not_change_lifecycle_state() -> None:
    """Cancellation is not wrapped and does not poison the started agent."""
    agent = BlockingIntegerAgent()
    await start(agent)
    task = asyncio.create_task(agent.run(1))
    await asyncio.wait_for(agent.entered.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert agent.lifecycle_state is LifecycleState.STARTED


@pytest.mark.asyncio
async def test_caller_owned_timeout_propagates_and_keeps_agent_started() -> None:
    """An asyncio timeout owned by the caller is not converted to AgentError."""
    agent = BlockingIntegerAgent()
    await start(agent)
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.02):
            await agent.run(1)

    assert agent.entered.is_set()
    assert agent.lifecycle_state is LifecycleState.STARTED


class TimeoutAgent(BaseAgent[None, None]):
    """Agent that raises an explicit timeout exception from execution."""

    def __init__(self, error: TimeoutError) -> None:
        """Store the timeout instance for identity assertions."""
        super().__init__("timeout-agent")
        self.error = error

    async def _execute(self, agent_input: None) -> None:
        """Raise the explicit timeout unchanged."""
        raise self.error


class ProcessControlAgent(BaseAgent[None, None]):
    """Agent that raises a process-control exception unchanged."""

    def __init__(self, error: BaseException) -> None:
        """Store the process-control exception."""
        super().__init__("process-control-agent")
        self.error = error

    async def _execute(self, agent_input: None) -> None:
        """Raise the stored process-control exception."""
        raise self.error


@pytest.mark.asyncio
async def test_explicit_timeout_error_propagates_by_identity() -> None:
    """TimeoutError raised by an agent is not wrapped as AgentError."""
    expected = TimeoutError("caller deadline")
    agent = TimeoutAgent(expected)
    await start(agent)

    with pytest.raises(TimeoutError) as captured:
        await agent.run(None)

    assert captured.value is expected
    assert agent.lifecycle_state is LifecycleState.STARTED


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.asyncio
async def test_process_control_exceptions_propagate_without_wrapping(
    exception_type: type[BaseException],
) -> None:
    """Process-control exceptions pass through the execution boundary."""
    expected = exception_type("process control")
    agent = ProcessControlAgent(expected)
    await start(agent)

    with pytest.raises(exception_type) as captured:
        await agent.run(None)

    assert captured.value is expected
    assert agent.lifecycle_state is LifecycleState.STARTED


@pytest.mark.asyncio
async def test_stop_can_finish_while_execution_is_awaiting() -> None:
    """Started-state admission does not serialize run against shutdown."""
    agent = BlockingIntegerAgent()
    await start(agent)
    task = asyncio.create_task(agent.run(5))
    await asyncio.wait_for(agent.entered.wait(), timeout=2)

    await agent.stop()
    assert agent.lifecycle_state is LifecycleState.STOPPED
    assert not task.done()

    agent.release.set()
    assert await task == "5"
    assert agent.lifecycle_state is LifecycleState.STOPPED


@pytest.mark.parametrize("name", ["", "  \t\n", None, 42])
def test_base_agent_rejects_invalid_names(name: object) -> None:
    """BaseAgent preserves BaseComponent name validation."""
    with pytest.raises(ValueError, match="component name"):
        IntegerAgentWithName(cast(str, name))


class IntegerAgentWithName(BaseAgent[int, str]):
    """Concrete named subclass for constructor validation tests."""

    def __init__(self, name: str) -> None:
        """Initialize with a caller-supplied component name."""
        super().__init__(name)

    async def _execute(self, agent_input: int) -> str:
        """Return the input as text."""
        return str(agent_input)


@pytest.mark.asyncio
async def test_base_agent_specialization_is_compatible_with_agent_protocol() -> None:
    """A context/result specialization assigns to the existing Agent protocol."""
    concrete_agent = ContextAgent()
    await concrete_agent.initialize()
    await concrete_agent.start()
    agent: Agent = concrete_agent

    result = await agent.run(AgentContext(goal="typed compatibility"))

    assert result == AgentResult(content="typed compatibility", metadata={"agent": "context-agent"})
