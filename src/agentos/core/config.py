from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentOSSettings(BaseSettings):
    """Runtime settings shared by AgentOS framework components."""

    model_config = SettingsConfigDict(env_prefix="AGENTOS_", env_file=".env", extra="ignore")

    environment: str = Field(default="development", description="Deployment environment name.")
    log_level: str = Field(default="INFO", description="Application log level.")
