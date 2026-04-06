"""CLI command: mr-lang init — interactive wizard to scaffold a new plugin project."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from mr_lang.plugins.scaffold import TelegramWizardConfig, WizardConfig, scaffold_project

console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Provider / model defaults
# ---------------------------------------------------------------------------

_PROVIDERS = {
    "ollama": {"label": "Ollama (local or cloud)", "model_hint": "llama3"},
    "openai": {"label": "OpenAI", "model_hint": "gpt-4o"},
    "anthropic": {"label": "Anthropic", "model_hint": "claude-sonnet-4-6"},
}

_RESERVED_NAMES = {
    "test",
    "tests",
    "os",
    "sys",
    "io",
    "re",
    "json",
    "typing",
    "types",
    "logging",
    "math",
    "time",
    "datetime",
    "collections",
    "abc",
    "ast",
    "asyncio",
    "http",
    "email",
    "html",
    "xml",
    "csv",
    "sqlite3",
    "mr_lang",
    "mr-lang",
    "pip",
    "setup",
    "pkg_resources",
    "importlib",
}

_AUTH_MODES = {
    "invite": "Users need an invite code (admins generate with /invite)",
    "allowlist": "Only pre-approved Telegram user IDs can chat",
    "open": "Anyone can chat with the bot",
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
    description: str = typer.Option("", "--description", "-d", help="Short description"),
    path: str = typer.Option("plugins", "--path", "-p", help="Parent directory for the plugin"),
    no_wizard: bool = typer.Option(False, "--no-wizard", help="Skip interactive wizard"),
) -> None:
    """Create a new plugin project. Runs an interactive wizard by default."""
    if no_wizard:
        if not name:
            console.print("[red]Error:[/red] Project name is required in non-interactive mode.")
            raise typer.Exit(code=1)
        _run_quick(name, description, path)
    else:
        _run_wizard(name, path)


# ---------------------------------------------------------------------------
# Quick (non-interactive) mode
# ---------------------------------------------------------------------------


def _run_quick(name: str, description: str, path: str) -> None:
    desc = description or f"A mr_lang plugin: {name.replace('-', ' ').title()}"
    try:
        root = scaffold_project(name=name, path=Path(path), description=desc)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    _print_success(name, root, WizardConfig())


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
        "  Project name [dim](kebab-case, e.g. my-tutor)[/dim]",
        default=initial_name or "",
    ).strip()
    if not wiz.name:
        console.print("[red]Name is required.[/red]")
        raise typer.Exit(code=1)
    module_name = wiz.name.replace("-", "_")
    if module_name in _RESERVED_NAMES or wiz.name in _RESERVED_NAMES:
        console.print(
            f"[red]'{wiz.name}' conflicts with a Python stdlib or framework module. "
            f"Pick a different name (e.g. my-{wiz.name}).[/red]"
        )
        raise typer.Exit(code=1)

    # ── Step 2: Description & Author ──────────────────────────────────
    _step_header(2, "About")
    display = wiz.name.replace("-", " ").title()
    wiz.description = Prompt.ask(
        "  Description",
        default=f"A mr_lang plugin: {display}",
    )
    wiz.author = Prompt.ask("  Author name", default="")

    # ── Step 3: Agent personality ─────────────────────────────────────
    _step_header(3, "Agent Personality")
    wiz.agent_name = Prompt.ask("  Agent display name", default=display)
    wiz.agent_role = Prompt.ask(
        "  Agent role [dim](e.g. Math Tutor, Code Reviewer, Support Agent)[/dim]",
        default="",
    )
    wiz.language = Prompt.ask("  Language(s)", default="English")
    wiz.personality = Prompt.ask(
        "  Personality [dim](one-liner or press Enter for default)[/dim]",
        default="",
    )

    # ── Step 4: Model provider ────────────────────────────────────────
    _step_header(4, "Model Provider")
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

    model_hint = _PROVIDERS[wiz.provider]["model_hint"]
    wiz.model = Prompt.ask(
        f"  Model name [dim](e.g. {model_hint})[/dim]",
        default="",
    )

    if wiz.provider == "ollama":
        wiz.ollama_base_url = Prompt.ask(
            "  Ollama base URL [dim](leave empty for local default)[/dim]",
            default="",
        )

    # ── Step 5: Memory & RAG ─────────────────────────────────────────
    _step_header(5, "Memory & Knowledge")
    wiz.enable_memory = Confirm.ask(
        "  Enable agent memory? [dim](remember/recall facts about users)[/dim]",
        default=True,
    )
    wiz.enable_rag = Confirm.ask(
        "  Enable knowledge base (RAG)? [dim](search documents/textbooks)[/dim]",
        default=False,
    )
    if wiz.enable_rag:
        rag_choices = ["chroma", "faiss"]
        raw_rag = Prompt.ask(
            "  RAG backend [dim](chroma, faiss)[/dim]",
            default="chroma",
        ).strip()
        wiz.rag_backend = raw_rag if raw_rag in rag_choices else "chroma"
    if wiz.enable_memory or wiz.enable_rag:
        wiz.embedding_model = Prompt.ask(
            "  Embedding model",
            default="nomic-embed-text",
        )

    # ── Step 6: Telegram ─────────────────────────────────────────────
    _step_header(6, "Telegram Bot")
    wiz.enable_telegram = Confirm.ask("  Enable Telegram bot?", default=False)

    if wiz.enable_telegram:
        tg = TelegramWizardConfig()

        tg.bot_token = Prompt.ask(
            "  Bot token [dim](from @BotFather, or leave empty to set later)[/dim]",
            default="",
        ).strip()

        # Auth mode
        console.print()
        for i, (mode, desc) in enumerate(_AUTH_MODES.items(), 1):
            console.print(f"    [bold cyan]{i}[/bold cyan]  {mode} — {desc}")
        raw_auth = Prompt.ask("  Auth mode", default="1").strip()
        auth_keys = list(_AUTH_MODES.keys())
        if raw_auth.isdigit() and 1 <= int(raw_auth) <= len(auth_keys):
            tg.auth_mode = auth_keys[int(raw_auth) - 1]
        elif raw_auth in _AUTH_MODES:
            tg.auth_mode = raw_auth
        else:
            tg.auth_mode = "invite"

        # Admin user IDs
        raw_admins = Prompt.ask(
            "  Admin Telegram user ID(s) [dim](comma-separated, or empty)[/dim]",
            default="",
        ).strip()
        if raw_admins:
            tg.admin_user_ids = _parse_int_list(raw_admins)
            # Admins are also allowed users by default
            tg.allowed_user_ids = list(tg.admin_user_ids)

        if tg.auth_mode == "allowlist":
            raw_allowed = Prompt.ask(
                "  Allowed user ID(s) [dim](comma-separated, admins already included)[/dim]",
                default="",
            ).strip()
            if raw_allowed:
                extra = _parse_int_list(raw_allowed)
                tg.allowed_user_ids = list(set(tg.allowed_user_ids) | set(extra))

        wiz.telegram = tg

    # ── Step 7: MCP servers ──────────────────────────────────────────
    _step_header(7, "External MCP Servers")
    add_mcp = Confirm.ask(
        "  Connect to external MCP servers? [dim](optional)[/dim]",
        default=False,
    )
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
    summary.add_row("Description", wiz.description)
    summary.add_row("Author", wiz.author or "[dim]not set[/dim]")
    agent_desc = wiz.agent_name
    if wiz.agent_role:
        agent_desc += f" ({wiz.agent_role})"
    summary.add_row("Agent", agent_desc)
    summary.add_row("Language", wiz.language)
    provider_desc = wiz.provider
    if wiz.model:
        provider_desc += f" / {wiz.model}"
    if wiz.ollama_base_url:
        provider_desc += f" @ {wiz.ollama_base_url}"
    summary.add_row("Provider", provider_desc)

    # Features
    features: list[str] = []
    if wiz.enable_memory:
        features.append("memory")
    if wiz.enable_rag:
        features.append(f"RAG ({wiz.rag_backend})")
    if wiz.enable_telegram:
        tg_desc = "Telegram"
        if wiz.telegram:
            tg_desc += f" ({wiz.telegram.auth_mode})"
            if wiz.telegram.bot_token:
                tg_desc += " [green]token set[/green]"
            else:
                tg_desc += " [yellow]token not set[/yellow]"
        features.append(tg_desc)
    if wiz.mcp_servers:
        features.append(f"{len(wiz.mcp_servers)} MCP server(s)")
    summary.add_row("Features", ", ".join(features) if features else "[dim]none[/dim]")

    console.print(summary)
    console.print()

    if not Confirm.ask("  Create this project?", default=True):
        console.print("[dim]Cancelled.[/dim]")
        raise typer.Exit()

    # ── Create ────────────────────────────────────────────────────────
    try:
        root = scaffold_project(
            name=wiz.name,
            path=Path(path),
            description=wiz.description,
            wizard=wiz,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    _print_success(wiz.name, root, wiz)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step_header(number: int, title: str) -> None:
    console.print()
    text = Text()
    text.append(f"  Step {number}", style="bold cyan")
    text.append(f"  {title}", style="bold")
    console.print(text)


def _parse_int_list(raw: str) -> list[int]:
    """Parse comma-separated integers, skipping invalid values."""
    result: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
        elif part:
            console.print(f"  [yellow]Skipping invalid ID: {part}[/yellow]")
    return result


def _print_success(name: str, root: Path, wiz: WizardConfig) -> None:
    module = name.replace("-", "_")
    # Show path relative to cwd for cleaner output
    try:
        rel_root = root.relative_to(Path.cwd())
    except ValueError:
        rel_root = root

    lines = [
        f"[bold green]Project created:[/bold green] {rel_root}",
        "",
        "[bold]Next steps:[/bold]",
        f"  pip install -e {rel_root}",
        f"  mr-lang chat --plugin {name}",
    ]

    if wiz.enable_rag:
        if wiz.rag_backend == "chroma":
            rag_pkg = "langchain-chroma"
        else:
            rag_pkg = "langchain-community faiss-cpu"
        lines += [
            "",
            "[yellow]RAG:[/yellow] Install the vector store backend:",
            f"  pip install {rag_pkg}",
        ]

    if wiz.enable_telegram and (not wiz.telegram or not wiz.telegram.bot_token):
        lines += [
            "",
            f"[yellow]Telegram:[/yellow] Set your bot token in [bold]{rel_root}/.env[/bold]:",
            f"  {module.upper()}_TELEGRAM_TOKEN=<your-token-from-BotFather>",
        ]

    if wiz.enable_telegram:
        lines += [
            "",
            f"  mr-lang telegram --plugin {name}",
        ]

    lines += [
        "",
        f"[dim]Edit {rel_root}/workspace/*.md to customize your agent.",
        f"Add tools in {rel_root}/src/{module}/tools/__init__.py",
        f"Add skills in {rel_root}/src/{module}/skills/[/dim]",
    ]

    console.print()
    console.print(
        Panel(
            "\n".join(lines),
            border_style="green",
            padding=(1, 2),
        )
    )
