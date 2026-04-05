"""CLI command: mr-lang init — scaffold a new plugin project."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from mr_lang.plugins.scaffold import TEMPLATES, scaffold_project

console = Console(stderr=True)

init_app = typer.Typer(
    name="init", help="Scaffold a new mr_lang plugin project.", invoke_without_command=True
)


@init_app.callback(invoke_without_command=True)
def init(
    name: str = typer.Argument(..., help="Project name (kebab-case, e.g. 'my-plugin')"),
    template: str = typer.Option(
        "",
        "--template",
        "-t",
        help=f"Project template: {', '.join(sorted(TEMPLATES))}",
    ),
    description: str = typer.Option("", "--description", "-d", help="Short description"),
    path: str = typer.Option(".", "--path", "-p", help="Parent directory for the project"),
) -> None:
    """Create a new plugin project with a working directory structure."""
    # Interactive mode when template is not provided
    if not template:
        template = _ask_template()
    if not description:
        description = _ask_description(name)

    try:
        project_root = scaffold_project(
            name=name,
            path=Path(path),
            template=template,
            description=description,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"\n[green]Created plugin project:[/green] {project_root}")
    console.print("\nNext steps:")
    console.print(f"  cd {name}")
    console.print("  pip install -e .")
    console.print("  mr-lang chat --workspace ./workspace")


def _ask_template() -> str:
    """Prompt user to pick a template."""
    choices = sorted(TEMPLATES)
    console.print("\n[bold]Available templates:[/bold]")
    for i, t in enumerate(choices, 1):
        console.print(f"  {i}. {t}")
    while True:
        raw = typer.prompt("Select template (number or name)", default="1")
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        elif raw in TEMPLATES:
            return raw
        console.print("[yellow]Invalid choice, try again.[/yellow]")


def _ask_description(name: str) -> str:
    """Prompt user for a project description."""
    display = name.replace("-", " ").title()
    return typer.prompt("Description", default=f"A mr_lang plugin: {display}")
