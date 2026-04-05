"""CLI command: mr-lang plugin — manage plugins."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

console = Console(stderr=True)

plugin_app = typer.Typer(name="plugin", help="Discover and manage mr_lang plugins.")


@plugin_app.command("list")
def list_plugins() -> None:
    """List all discovered plugins."""
    from mr_lang.plugins.loader import PluginLoader

    manifests = PluginLoader.discover_plugins()

    if not manifests:
        console.print("[dim]No plugins discovered.[/dim]")
        raise typer.Exit()

    table = Table(title="Discovered Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Version")
    table.add_column("Description")
    table.add_column("Tools Module")
    table.add_column("Workspace")

    for m in manifests:
        table.add_row(
            m.name,
            m.version,
            m.description[:60] if m.description else "",
            m.tools_module or "",
            str(m.workspace_dir) if m.workspace_dir else "",
        )
    console.print(table)


@plugin_app.command("info")
def plugin_info(
    name: str = typer.Argument(..., help="Plugin name to inspect"),
) -> None:
    """Show detailed information about a plugin."""
    from mr_lang.plugins.loader import PluginLoader

    manifests = PluginLoader.discover_plugins()
    match = next((m for m in manifests if m.name == name), None)

    if match is None:
        console.print(f"[red]Plugin '{name}' not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold cyan]{match.name}[/bold cyan] v{match.version}")
    console.print(f"  Description:  {match.description}")
    console.print(f"  Author:       {match.author}")
    console.print(f"  Workspace:    {match.workspace_dir or '(none)'}")
    console.print(f"  Skills dir:   {match.skills_dir or '(none)'}")
    console.print(f"  Tools module: {match.tools_module or '(none)'}")
    console.print(f"  CLI module:   {match.cli_module or '(none)'}")
    console.print(f"  MCP servers:  {match.mcp_servers or '(none)'}")
    console.print(f"  Dependencies: {match.dependencies or '(none)'}")


@plugin_app.command("activate")
def activate_plugin(
    name: str = typer.Argument(..., help="Plugin name to activate"),
) -> None:
    """Activate a plugin, loading its tools and skills."""
    from mr_lang.core.registry import SkillRegistry, ToolRegistry
    from mr_lang.plugins.loader import PluginLoader

    manifests = PluginLoader.discover_plugins()
    match = next((m for m in manifests if m.name == name), None)

    if match is None:
        console.print(f"[red]Plugin '{name}' not found.[/red]")
        raise typer.Exit(code=1)

    tool_reg = ToolRegistry()
    skill_reg = SkillRegistry()

    try:
        PluginLoader.activate_plugin(match, tool_reg, skill_reg)
    except Exception as exc:
        console.print(f"[red]Activation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Activated '{name}'[/green]")
    console.print(f"  Tools loaded:  {len(tool_reg)}")
    console.print(f"  Skills loaded: {len(skill_reg)}")
