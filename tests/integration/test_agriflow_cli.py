from __future__ import annotations

from apps.agriflow.main import app
from typer.testing import CliRunner


def test_health_command_reports_application_status() -> None:
    """The historical root invocation should report application health once."""
    runner = CliRunner()

    result = runner.invoke(app)

    assert result.exit_code == 0
    assert "agriflow is healthy" in result.stdout
    assert result.stdout.count("agriflow is healthy") == 1


def test_explicit_health_command_reports_application_status() -> None:
    """The explicit health subcommand should report application status."""
    result = CliRunner().invoke(app, ["health"])

    assert result.exit_code == 0
    assert "agriflow is healthy" in result.stdout
    assert result.stdout.count("agriflow is healthy") == 1


def test_help_lists_health_command() -> None:
    """CLI help should list the explicit health subcommand."""
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "health" in result.stdout


def test_invalid_command_returns_nonzero_exit_status() -> None:
    """Unknown subcommands should remain an error."""
    result = CliRunner().invoke(app, ["unknown-command"])

    assert result.exit_code != 0
    assert "unknown-command" in result.output
