from __future__ import annotations

from agentos.core.config import AgentOSSettings


def test_agentos_settings_have_safe_defaults() -> None:
    """AgentOS settings should provide local-development defaults."""
    settings = AgentOSSettings()

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
