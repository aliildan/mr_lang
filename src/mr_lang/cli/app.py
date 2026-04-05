"""mr-lang CLI — main entry point."""

from __future__ import annotations

import typer

from mr_lang import __version__

app = typer.Typer(
    name="mr-lang",
    help="Agent orchestration framework built on LangChain/LangGraph.",
    no_args_is_help=True,
)


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
def config() -> None:
    """Show current configuration."""
    from rich.console import Console

    from mr_lang.config import MrLangConfig

    console = Console(stderr=True)
    cfg = MrLangConfig()
    console.print_json(cfg.model_dump_json(indent=2))
