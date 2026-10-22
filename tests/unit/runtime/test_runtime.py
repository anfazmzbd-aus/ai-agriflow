from __future__ import annotations

from agentos.core.config import AgentOSSettings
from agentos.runtime import Runtime


def test_runtime_can_be_created_from_settings() -> None:
    """Runtime should preserve explicit settings."""
    settings = AgentOSSettings(environment="test", log_level="WARNING")

    runtime = Runtime.from_settings(settings)

    assert runtime.settings == settings
