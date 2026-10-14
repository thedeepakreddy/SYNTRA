"""Command implementations for the DevSwarm CLI."""

import asyncio
from pathlib import Path
import typer
import uvicorn
from rich.panel import Panel
from devswarm.checkpoints.engine import get_checkpoint_engine
from devswarm.cli.ui import (
    console,
    render_banner,
    render_checkpoints_table,
    render_sessions_table,
)
from devswarm.core.config import AutonomyMode, get_settings
from devswarm.core.events import Event, EventType, get_event_bus
from devswarm.core.telemetry import get_telemetry
from devswarm.storage.database import get_db_manager
from devswarm.storage.repositories import SessionRepository
from devswarm.swarm.engine import SwarmEngine


def run_command(
    objective: str = typer.Argument(..., help="Software engineering task or feature objective"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Target workspace path (defaults to sandboxed temp)"),
    mode: str = typer.Option("semi_autonomous", "--mode", "-m", help="Autonomy mode: autonomous, semi_autonomous, supervised, strict_approval"),
    iterations: int = typer.Option(3, "--iterations", "-i", help="Maximum review/test self-healing cycles"),
) -> None:
    """Run an autonomous multi-agent engineering workflow."""
    render_banner()
    console.print(f"[bold green]Starting Swarm Execution...[/bold green]")
    console.print(f"[bold]Objective:[/bold] {objective}")
    console.print(f"[bold]Autonomy Mode:[/bold] {mode}")

    parsed_mode = AutonomyMode(mode)

    # Event logger hook
    async def log_event(event: Event):
        if event.type == EventType.AGENT_THOUGHT:
            role = event.agent_role or "agent"
            console.print(f"[cyan]▶ [{role.upper()}][/cyan] {event.data.get('thought', '')[:120]}...")
        elif event.type == EventType.AGENT_TOOL_CALL_STARTED:
            console.print(f"  [yellow]⚡ Calling Tool:[/yellow] {event.data.get('tool')} {event.data.get('arguments')}")
        elif event.type == EventType.CHECKPOINT_REQUESTED:
            console.print(Panel(
                f"[bold red]CHECKPOINT REQUIRED[/bold red]\n"
                f"Action: {event.data.get('action_type')}\n"
                f"Risk: {event.data.get('risk_level')}\n"
                f"Description: {event.data.get('description')}\n"
                f"Use `devswarm checkpoint resolve {event.data.get('checkpoint_id')} --decision approve`",
                border_style="red",
            ))

    get_event_bus().subscribe(log_event)

    async def _run():
        engine = SwarmEngine(
            workspace_dir=workspace,
            autonomy_mode=parsed_mode,
        )
        final_state = await engine.execute_task(objective=objective, max_iterations=iterations)
        return final_state

    state = asyncio.run(_run())

    if state.is_completed and not state.error:
        console.print(Panel(
            f"[bold green]✓ Swarm Workflow Successfully Completed![/bold green]\n"
            f"Review Status: {'Approved' if state.review_approved else 'Max iterations reached'}\n"
            f"Security Status: {'Passed' if state.security_passed else 'Warnings recorded'}",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[bold red]✗ Swarm Execution Terminated with Error[/bold red]\n{state.error}",
            border_style="red",
        ))


def serve_command(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host address"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port number"),
    reload: bool = typer.Option(False, "--reload", help="Enable live code reloading"),
) -> None:
    """Start the production DevSwarm FastAPI & WebSocket server."""
    render_banner()
    console.print(f"[bold green]Starting API & WebSocket Server on http://{host}:{port}...[/bold green]")
    uvicorn.run("devswarm.api.app:app", host=host, port=port, reload=reload)


def list_sessions_command(limit: int = typer.Option(20, "--limit", "-l")) -> None:
    """List historical engineering sessions."""
    async def _fetch():
        db = get_db_manager()
        async with db.session() as s:
            repo = SessionRepository(s)
            return await repo.list_recent(limit=limit)

    sessions = asyncio.run(_fetch())
    render_sessions_table(sessions)


def list_checkpoints_command() -> None:
    """List pending hybrid autonomy checkpoints."""
    engine = get_checkpoint_engine()
    checkpoints = engine.list_checkpoints()
    render_checkpoints_table(checkpoints)


def resolve_checkpoint_command(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID to resolve"),
    decision: str = typer.Option("approve", "--decision", "-d", help="Decision: approve, reject, modify"),
    feedback: str = typer.Option("", "--feedback", "-f", help="Corrective feedback (required for reject)"),
) -> None:
    """Resolve a pending checkpoint gate."""
    engine = get_checkpoint_engine()

    async def _resolve():
        return await engine.resolve(checkpoint_id=checkpoint_id, decision=decision, feedback=feedback or None)

    resolved = asyncio.run(_resolve())
    console.print(f"[bold green]Checkpoint {resolved.checkpoint_id[:8]} resolved as {resolved.status.value.upper()}[/bold green]")


def status_command() -> None:
    """Display system status, Gemini configuration, and telemetry."""
    render_banner()
    settings = get_settings()
    summary = get_telemetry().get_summary()

    status_info = (
        f"[bold]Default Model:[/bold] {settings.default_model}\n"
        f"[bold]Reasoning Model:[/bold] {settings.reasoning_model}\n"
        f"[bold]Fast Model:[/bold] {settings.fast_model}\n"
        f"[bold]Gemini API Key Configured:[/bold] {'[green]Yes[/green]' if settings.is_api_key_configured() else '[yellow]No (Using Offline Mock Provider)[/yellow]'}\n"
        f"[bold]Default Autonomy Mode:[/bold] {settings.autonomy_mode.value}\n"
        f"[bold]Database URL:[/bold] {settings.database_url}\n"
        f"[bold]Total LLM Invocations:[/bold] {summary['total_invocations']}\n"
        f"[bold]Total Tokens Consumed:[/bold] {summary['total_tokens']}\n"
        f"[bold]Estimated Cost (USD):[/bold] ${summary['total_estimated_cost_usd']:.6f}"
    )
    console.print(Panel(status_info, title="System Diagnostics & Telemetry", border_style="cyan"))
