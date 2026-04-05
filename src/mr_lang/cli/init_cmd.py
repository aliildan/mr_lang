"""CLI command: mr-lang init — interactive wizard to scaffold a new plugin project."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from mr_lang.plugins.scaffold import TEMPLATES, WizardConfig, scaffold_project

console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Provider / model defaults
# ---------------------------------------------------------------------------

_PROVIDERS = {
    "ollama": {"label": "Ollama (local or cloud)"},
    "openai": {"label": "OpenAI"},
    "anthropic": {"label": "Anthropic"},
}

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

init_app = typer.Typer(
    name="init",
    help="Scaffold a new mr_lang plugin project.",
    invoke_without_command=True,
)


@init_app.callback(invoke_without_command=True)
def init(
    name: str = typer.Argument(None, help="Project name (kebab-case)"),
    template: str = typer.Option("", "--template", "-t", help="Skip wizard, use template directly"),
    description: str = typer.Option("", "--description", "-d", help="Short description"),
    path: str = typer.Option(".", "--path", "-p", help="Parent directory"),
    no_wizard: bool = typer.Option(False, "--no-wizard", help="Skip interactive wizard"),
) -> None:
    """Create a new plugin project. Runs an interactive wizard by default."""
    if no_wizard or template:
        # Non-interactive mode
        if not name:
            console.print("[red]Error:[/red] Project name is required in non-interactive mode.")
            raise typer.Exit(code=1)
        _run_quick(name, template or "basic", description, path)
    else:
        _run_wizard(name, path)


# ---------------------------------------------------------------------------
# Quick (non-interactive) mode
# ---------------------------------------------------------------------------


def _run_quick(name: str, template: str, description: str, path: str) -> None:
    desc = description or f"A mr_lang plugin: {name.replace('-', ' ').title()}"
    try:
        root = scaffold_project(name=name, path=Path(path), template=template, description=desc)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    _print_success(name, root)


# ---------------------------------------------------------------------------
# Interactive wizard
# ---------------------------------------------------------------------------


def _run_wizard(initial_name: str | None, path: str) -> None:
    console.print()
    console.print(
        Panel(
            "[bold]mr-lang project wizard[/bold]\n"
            "Create a new agent project step by step.\n"
            "Press [dim]Ctrl+C[/dim] to cancel at any time.",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    wiz = WizardConfig()

    # ── Step 1: Project name ──────────────────────────────────────────
    _step_header(1, "Project Name")
    wiz.name = Prompt.ask(
        "  Project name [dim](kebab-case)[/dim]",
        default=initial_name or "",
    ).strip()
    if not wiz.name:
        console.print("[red]Name is required.[/red]")
        raise typer.Exit(code=1)

    # ── Step 2: Template ──────────────────────────────────────────────
    _step_header(2, "Template")
    choices = sorted(TEMPLATES)
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=4)
    table.add_column("Template")
    for i, tmpl in enumerate(choices, 1):
        table.add_row(f"  {i}", tmpl)
    console.print(table)

    raw = Prompt.ask("  Select template", default="1").strip()
    if raw.isdigit() and 1 <= int(raw) <= len(choices):
        wiz.template = choices[int(raw) - 1]
    elif raw in TEMPLATES:
        wiz.template = raw
    else:
        console.print(f"[yellow]Unknown '{raw}', defaulting to 'basic'[/yellow]")
        wiz.template = "basic"

    # ── Step 3: Description & Author ──────────────────────────────────
    _step_header(3, "About")
    display = wiz.name.replace("-", " ").title()
    wiz.description = Prompt.ask(
        "  Description",
        default=f"A mr_lang plugin: {display}",
    )
    wiz.author = Prompt.ask("  Author name", default="")

    # ── Step 4: Agent personality ─────────────────────────────────────
    _step_header(4, "Agent Personality")
    wiz.agent_name = Prompt.ask("  Agent display name", default=display)
    wiz.agent_role = Prompt.ask(
        "  Agent role [dim](e.g., Teaching Assistant, Code Reviewer)[/dim]",
        default="",
    )
    wiz.language = Prompt.ask("  Language(s)", default="English")
    wiz.personality = Prompt.ask(
        "  Personality [dim](one-liner or press Enter for default)[/dim]",
        default="",
    )

    # ── Step 5: Model provider ────────────────────────────────────────
    _step_header(5, "Model Provider")
    ptable = Table(show_header=False, box=None, padding=(0, 2))
    ptable.add_column("Key", style="bold cyan", width=4)
    ptable.add_column("Provider")
    provider_keys = list(_PROVIDERS.keys())
    for i, pk in enumerate(provider_keys, 1):
        ptable.add_row(f"  {i}", _PROVIDERS[pk]["label"])
    console.print(ptable)

    raw_p = Prompt.ask("  Select provider", default="1").strip()
    if raw_p.isdigit() and 1 <= int(raw_p) <= len(provider_keys):
        wiz.provider = provider_keys[int(raw_p) - 1]
    elif raw_p in _PROVIDERS:
        wiz.provider = raw_p
    else:
        wiz.provider = "ollama"

    wiz.model = Prompt.ask(
        "  Model name [dim](e.g. llama3, gpt-4o, claude-sonnet-4-6)[/dim]",
        default="",
    )

    if wiz.provider == "ollama":
        wiz.ollama_base_url = Prompt.ask(
            "  Ollama base URL [dim](leave empty for local default)[/dim]",
            default="",
        )

    # ── Step 6: Adapters & MCP ────────────────────────────────────────
    _step_header(6, "Integrations")
    wiz.enable_telegram = Confirm.ask("  Enable Telegram bot?", default=False)

    add_mcp = Confirm.ask("  Connect to external MCP servers?", default=False)
    if add_mcp:
        console.print("  [dim]Enter MCP server URLs one per line. Empty line to finish.[/dim]")
        while True:
            url = Prompt.ask("  MCP server URL", default="").strip()
            if not url:
                break
            wiz.mcp_servers.append(url)
        if wiz.mcp_servers:
            console.print(f"  [green]Added {len(wiz.mcp_servers)} MCP server(s)[/green]")

    # ── Summary & Confirm ─────────────────────────────────────────────
    console.print()
    summary = Table(title="Project Summary", show_header=False, border_style="cyan")
    summary.add_column("Field", style="bold")
    summary.add_column("Value")
    summary.add_row("Name", wiz.name)
    summary.add_row("Template", wiz.template)
    summary.add_row("Description", wiz.description)
    summary.add_row("Author", wiz.author or "[dim]not set[/dim]")
    agent_desc = wiz.agent_name
    if wiz.agent_role:
        agent_desc += f" ({wiz.agent_role})"
    summary.add_row("Agent", agent_desc)
    summary.add_row("Language", wiz.language)
    provider_desc = wiz.provider
    if wiz.model:
        provider_desc += f"/{wiz.model}"
    if wiz.ollama_base_url:
        provider_desc += f" @ {wiz.ollama_base_url}"
    summary.add_row("Provider", provider_desc)
    summary.add_row("Telegram", "yes" if wiz.enable_telegram else "no")
    summary.add_row("MCP servers", str(len(wiz.mcp_servers)))
    console.print(summary)
    console.print()

    if not Confirm.ask("  Create this project?", default=True):
        console.print("[dim]Cancelled.[/dim]")
        raise typer.Exit()

    # ── Create ────────────────────────────────────────────────────────
    template = wiz.template
    if wiz.enable_telegram and template != "telegram-bot":
        template = "telegram-bot"

    try:
        root = scaffold_project(
            name=wiz.name,
            path=Path(path),
            template=template,
            description=wiz.description,
            wizard=wiz,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    _print_success(wiz.name, root)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step_header(number: int, title: str) -> None:
    console.print()
    text = Text()
    text.append(f"  Step {number}", style="bold cyan")
    text.append(f"  {title}", style="bold")
    console.print(text)


def _print_success(name: str, root: Path) -> None:
    console.print()
    console.print(
        Panel(
            f"[bold green]Project created:[/bold green] {root}\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"  cd {name}\n"
            f"  pip install -e .\n"
            f"  mr-lang chat --workspace ./workspace\n\n"
            f"[dim]Edit workspace/*.md files to customize your agent.\n"
            f"Add tools in src/{name.replace('-', '_')}/tools/__init__.py\n"
            f"Add skills in src/{name.replace('-', '_')}/skills/[/dim]",
            border_style="green",
            padding=(1, 2),
        )
    )
