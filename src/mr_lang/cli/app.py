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
    workspace: str = typer.Option(None, "--workspace", "-w", help="Path to workspace directory"),
    provider: str = typer.Option(None, "--provider", "-p", help="Model provider"),
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    plugin: str = typer.Option(
        None, "--plugin", help="Plugin name (isolates to this plugin's context)"
    ),
) -> None:
    """Start an interactive chat session with an agent."""
    import asyncio

    from mr_lang.cli.chat import run_chat

    asyncio.run(run_chat(workspace=workspace, provider=provider, model=model, plugin=plugin))


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
    workspace: str = typer.Option(None, "--workspace", "-w", help="Path to workspace directory"),
    provider: str = typer.Option(None, "--provider", "-p", help="Model provider"),
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    plugin: str = typer.Option(None, "--plugin", help="Plugin name to run bot for"),
) -> None:
    """Start the Telegram bot adapter."""
    import asyncio

    from mr_lang.cli.telegram_cmd import run_telegram

    asyncio.run(run_telegram(workspace=workspace, provider=provider, model=model, plugin=plugin))


@app.command()
def serve(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Path to workspace directory"),
    provider: str = typer.Option(None, "--provider", "-p", help="Model provider"),
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    host: str = typer.Option(None, "--host", help="Server host (default from config)"),
    port: int = typer.Option(None, "--port", help="Server port (default from config)"),
    plugin: str = typer.Option(
        None, "--plugin", help="Plugin name (isolates to this plugin's context)"
    ),
) -> None:
    """Start the MCP server adapter."""
    import asyncio

    from mr_lang.cli.serve_cmd import run_serve

    asyncio.run(
        run_serve(
            workspace=workspace,
            provider=provider,
            model=model,
            host=host,
            port=port,
            plugin=plugin,
        )
    )


@app.command()
def dashboard(
    host: str = typer.Option("127.0.0.1", "--host", help="Dashboard host"),
    port: int = typer.Option(8080, "--port", help="Dashboard port"),
    log_dir: str = typer.Option(None, "--log-dir", help="Path to log directory"),
) -> None:
    """Start the observability dashboard web UI."""
    try:
        from aiohttp import web
    except ImportError as err:
        typer.echo("Dashboard requires aiohttp: pip install aiohttp")
        raise typer.Exit(code=1) from err

    from mr_lang.api.routes import create_app
    from mr_lang.observability.collector import EventCollector

    collector = EventCollector(log_dir=log_dir or ".mr_lang/logs")
    app_instance = create_app(collector)
    typer.echo(f"Dashboard: http://{host}:{port}/dashboard")
    web.run_app(app_instance, host=host, port=port, print=lambda _: None)


@app.command()
def monitor(
    session: str = typer.Option(None, "--session", "-s", help="Show events for a specific session"),
    tail: bool = typer.Option(False, "--tail", "-t", help="Live tail of events"),
    log_dir: str = typer.Option(None, "--log-dir", help="Path to log directory"),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
) -> None:
    """View observability data: sessions, events, and live tail."""
    from mr_lang.cli.monitor_cmd import run_monitor

    run_monitor(session=session, tail=tail, log_dir=log_dir, output_json=output_json)


@app.command()
def rag(
    plugin: str = typer.Option(..., "--plugin", help="Plugin name to index into"),
    paths: list[str] = typer.Argument(  # noqa: B008
        None, help="Files or directories to index"
    ),
    chunk_size: int = typer.Option(
        None, "--chunk-size", help="Chunk size (default from plugin config)"
    ),
    chunk_overlap: int = typer.Option(
        None, "--chunk-overlap", help="Chunk overlap (default from plugin config)"
    ),
) -> None:
    """Index files into a plugin's RAG knowledge base."""
    if not paths:
        typer.echo("Usage: mr-lang rag --plugin <name> <file-or-dir> [...]")
        raise typer.Exit(code=1)

    from mr_lang.cli.rag_cmd import run_rag_index

    try:
        run_rag_index(
            plugin=plugin,
            paths=paths,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    except Exception as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def doctor() -> None:
    """Diagnose common setup issues."""
    from mr_lang.cli.doctor_cmd import run_doctor

    run_doctor()


@app.command()
def config() -> None:
    """Show current configuration."""
    from rich.console import Console

    from mr_lang.config import MrLangConfig

    console = Console(stderr=True)
    cfg = MrLangConfig()
    console.print_json(cfg.model_dump_json(indent=2))
