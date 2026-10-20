"""Terminal UI rendering helpers using Rich."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from syntra.checkpoints.models import Checkpoint
from syntra.storage.models import SessionModel

console = Console()


def render_banner() -> None:
    """Display startup banner."""
    banner_text = (
        "[bold cyan]SYNTRA[/bold cyan]: [bold white]Synchronized Intelligence for Autonomous Engineering[/bold white]\n"
        "[italic yellow]One Vision. Multiple AI Agents. Autonomous Engineering.[/italic yellow]\n"
        "[dim]Powered by Google Gemini (google-genai SDK) • Hybrid Autonomy Engine[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan"))


def render_sessions_table(sessions: list[SessionModel]) -> None:
    """Render sessions in a clean tabular view."""
    table = Table(title="SYNTRA Engineering Sessions", border_style="blue")
    table.add_column("Session ID", style="cyan", no_wrap=True)
    table.add_column("Objective", style="white")
    table.add_column("Status", style="magenta")
    table.add_column("Autonomy Mode", style="yellow")
    table.add_column("Updated At", style="dim")

    for s in sessions:
        status_color = "green" if s.status == "completed" else "yellow" if s.status == "running" else "red"
        table.add_row(
            s.id,
            s.objective[:60] + ("..." if len(s.objective) > 60 else ""),
            f"[{status_color}]{s.status}[/{status_color}]",
            s.autonomy_mode,
            s.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    console.print(table)


def render_checkpoints_table(checkpoints: list[Checkpoint]) -> None:
    """Render checkpoints in a table."""
    table = Table(title="Hybrid Autonomy Checkpoints", border_style="yellow")
    table.add_column("Checkpoint ID", style="cyan", no_wrap=True)
    table.add_column("Agent / Role", style="magenta")
    table.add_column("Action Type", style="blue")
    table.add_column("Risk Level", style="red")
    table.add_column("Status", style="yellow")
    table.add_column("Description", style="white")

    for cp in checkpoints:
        risk_color = "red" if cp.risk_level.value in ("critical", "high") else "yellow"
        table.add_row(
            cp.checkpoint_id[:8] + "...",
            f"{cp.agent_role} ({cp.agent_id[:6]})",
            cp.action_type.value,
            f"[{risk_color}]{cp.risk_level.value.upper()}[/{risk_color}]",
            cp.status.value,
            cp.description[:50],
        )

    console.print(table)


def render_diff(diff_content: str, filename: str = "diff") -> None:
    """Render syntax highlighted diff in terminal."""
    syntax = Syntax(diff_content, "diff", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"Proposed Changes: {filename}", border_style="yellow"))


def render_error(message: str, title: str = "Error") -> None:
    """Render error panel with fail-closed secret redaction."""
    from syntra.core.redactor import SecretRedactor

    clean_title = SecretRedactor.redact(title)
    clean_message = SecretRedactor.redact_deep_json_or_text(message)
    console.print(Panel(f"[bold red]{clean_message}[/bold red]", title=clean_title, border_style="red"))
