"""Tests for SYNTRA Typer CLI."""

from typer.testing import CliRunner
from syntra.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert "SYNTRA: Synchronized Intelligence for Autonomous Engineering" in result.stdout
    assert "Multiple AI Agents. Autonomous Engineering." in result.stdout
    assert "run" in result.stdout
    assert "serve" in result.stdout
    assert "status" in result.stdout


def test_cli_status():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "System Diagnostics & Telemetry" in result.stdout
    assert "Default Model" in result.stdout


def test_cli_sessions_list():
    result = runner.invoke(app, ["session", "list"])
    assert result.exit_code == 0
    assert "SYNTRA Engineering Sessions" in result.stdout


def test_cli_checkpoints_list():
    result = runner.invoke(app, ["checkpoint", "list"])
    assert result.exit_code == 0
    assert "Hybrid Autonomy Checkpoints" in result.stdout
