from __future__ import annotations

from agentos.agents import AgentContext, EchoAgent


async def test_echo_agent_returns_goal() -> None:
    """EchoAgent should return the requested goal."""
    agent = EchoAgent()

    result = await agent.run(AgentContext(goal="inspect field"))

    assert result.content == "inspect field"
    assert result.metadata["agent"] == "echo"
