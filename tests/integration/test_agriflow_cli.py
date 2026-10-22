from __future__ import annotations

from apps.agriflow.main import app
from typer.testing import CliRunner


def test_health_command_reports_application_status() -> None:
    """Health command should report the configured application status."""
    runner = CliRunner()

    result = runner.invoke(app)

    assert result.exit_code == 0
    assert "agriflow is healthy" in result.stdout
