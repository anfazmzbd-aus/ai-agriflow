from __future__ import annotations

import pytest
from examples.hello_agent import main


def test_hello_agent_example_runs(capsys: pytest.CaptureFixture[str]) -> None:
    """Hello agent example should produce a friendly message."""
    main()

    captured = capsys.readouterr()
    assert "Hello from AgentOS." in captured.out
