"""mr-lang CLI — main entry point."""

from __future__ import annotations

import typer

from mr_lang import __version__
from mr_lang.cli.init_cmd import init_app
from mr_lang.cli.plugin_cmd import plugin_app

app = typer.Typer(
    name="mr-lang",
    help="Agent orchestration framework built on LangChain/LangGraph.",
    no_args_is_help=True,
)

app.add_typer(init_app, name="init")
app.add_typer(plugin_app, name="plugin")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"mr-lang {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True, help="Show version"
    ),
) -> None:
    pass


@app.command()
def chat(
    workspace: str = typer.Option(
        None, "--workspace", "-w", help="Path to workspace directory"
    ),
    provider: str = typer.Option("ollama", "--provider", "-p", help="Model provider"),
    model: str = typer.Option("llama3", "--model", "-m", help="Model name"),
) -> None:
    """Start an interactive chat session with an agent."""
    import asyncio

    from mr_lang.cli.chat import run_chat

    asyncio.run(run_chat(workspace=workspace, provider=provider, model=model))


@app.command()
def tools(
    action: str = typer.Argument("list", help="Action: list, inspect"),
) -> None:
    """Manage tools."""
    from rich.console import Console
    from rich.table import Table

    from mr_lang.core.registry import ToolRegistry
    from mr_lang.tools.discovery import discover_tools_from_entry_points

    console = Console(stderr=True)
    registry = ToolRegistry()
    discover_tools_from_entry_points(registry)

    if action == "list":
        table = Table(title="Available Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        for tool in registry.list():
            table.add_row(tool.name, tool.description[:80])
        console.print(table)


@app.command()
def telegram(
    workspace: str = typer.Option(
        None, "--workspace", "-w", help="Path to workspace directory"
    ),
    provider: str = typer.Option("ollama", "--provider", "-p", help="Model provider"),
    model: str = typer.Option("llama3", "--model", "-m", help="Model name"),
) -> None:
    """Start the Telegram bot adapter."""
    import asyncio

    from mr_lang.cli.telegram_cmd import run_telegram

    asyncio.run(run_telegram(workspace=workspace, provider=provider, model=model))


@app.command()
def serve(
    workspace: str = typer.Option(
        None, "--workspace", "-w", help="Path to workspace directory"
    ),
    provider: str = typer.Option("ollama", "--provider", "-p", help="Model provider"),
    model: str = typer.Option("llama3", "--model", "-m", help="Model name"),
    host: str = typer.Option(None, "--host", help="Server host (default from config)"),
    port: int = typer.Option(None, "--port", help="Server port (default from config)"),
) -> None:
    """Start the MCP server adapter."""
    import asyncio

    from mr_lang.cli.serve_cmd import run_serve

    asyncio.run(
        run_serve(
            workspace=workspace, provider=provider, model=model, host=host, port=port
        )
    )


@app.command()
def monitor(
    session: str = typer.Option(None, "--session", "-s", help="Show events for a specific session"),
    tail: bool = typer.Option(False, "--tail", "-t", help="Live tail of events"),
    log_dir: str = typer.Option(None, "--log-dir", help="Path to log directory"),
) -> None:
    """View observability data: sessions, events, and live tail."""
    from mr_lang.cli.monitor_cmd import run_monitor

    run_monitor(session=session, tail=tail, log_dir=log_dir)


@app.command()
def config() -> None:
    """Show current configuration."""
    from rich.console import Console

    from mr_lang.config import MrLangConfig

    console = Console(stderr=True)
    cfg = MrLangConfig()
    console.print_json(cfg.model_dump_json(indent=2))
