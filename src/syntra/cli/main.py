"""Typer CLI entry point for SYNTRA."""

import typer

from syntra.cli.commands import (
    list_checkpoints_command,
    list_sessions_command,
    mcp_serve_command,
    resolve_checkpoint_command,
    run_command,
    serve_command,
    status_command,
)

app = typer.Typer(
    name="syntra",
    help="SYNTRA: Synchronized Intelligence for Autonomous Engineering — One Vision. Multiple AI Agents. Autonomous Engineering.",
    add_completion=False,
)

# Root commands
app.command("run", help="Run autonomous multi-agent software engineering workflow")(run_command)
app.command("serve", help="Launch the FastAPI & WebSocket backend server")(serve_command)
app.command("status", help="Display system status, Gemini configuration, and cost telemetry")(status_command)

# Sub-apps
session_app = typer.Typer(name="session", help="Manage engineering sessions")
session_app.command("list", help="List recent sessions")(list_sessions_command)
app.add_typer(session_app, name="session")

checkpoint_app = typer.Typer(name="checkpoint", help="Manage hybrid autonomy checkpoints")
checkpoint_app.command("list", help="List pending checkpoints")(list_checkpoints_command)
checkpoint_app.command("resolve", help="Approve, reject, or modify a checkpoint")(resolve_checkpoint_command)
app.add_typer(checkpoint_app, name="checkpoint")

mcp_app = typer.Typer(name="mcp", help="Model Context Protocol (MCP) server commands")
mcp_app.command("serve", help="Start MCP server over stdio for IDE / agent integration")(mcp_serve_command)
app.add_typer(mcp_app, name="mcp")


if __name__ == "__main__":
    app()
