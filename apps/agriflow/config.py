from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgriFlowSettings(BaseSettings):
    """Configuration for the AgriFlow application."""

    model_config = SettingsConfigDict(env_prefix="AGRIFLOW_", env_file=".env", extra="ignore")

    app_name: str = Field(default="agriflow", description="Application display name.")
    environment: str = Field(default="development", description="Deployment environment name.")
    log_level: str = Field(default="INFO", description="Application log level.")
