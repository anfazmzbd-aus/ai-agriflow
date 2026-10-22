from __future__ import annotations

import asyncio

from agentos.agents import AgentContext, EchoAgent


def main() -> None:
    """Run a tiny deterministic agent greeting."""
    result = asyncio.run(EchoAgent().run(AgentContext(goal="Hello from AgentOS.")))
    print(result.content)


if __name__ == "__main__":
    main()
