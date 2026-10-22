from __future__ import annotations

import typer

from agentos.core.config import AgentOSSettings
from agentos.runtime import Runtime
from apps.agriflow.config import AgriFlowSettings

app = typer.Typer(help="AgriFlow application CLI.")


@app.command()
def health() -> None:
    """Print a health-check message for local and container verification."""
    settings = AgriFlowSettings()
    Runtime.from_settings(
        AgentOSSettings(environment=settings.environment, log_level=settings.log_level)
    ).start()
    typer.echo(f"{settings.app_name} is healthy in {settings.environment}")


if __name__ == "__main__":
    app()
