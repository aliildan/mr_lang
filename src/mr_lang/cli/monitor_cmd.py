"""CLI monitor command — view sessions, events, and live-tail observability logs."""

from __future__ import annotations

import json
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.table import Table

from mr_lang.observability.events import ObservabilityEvent

DEFAULT_LOG_DIR = Path(".mr_lang/logs")


# ------------------------------------------------------------------
# Public entry-point called from the CLI
# ------------------------------------------------------------------


def run_monitor(
    session: str | None = None,
    tail: bool = False,
    log_dir: str | None = None,
) -> None:
    """Main dispatcher for ``mr-lang monitor``."""
    logs = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
    console = Console(stderr=True)

    if not logs.exists():
        console.print("[yellow]No log directory found.[/yellow] Nothing to show.")
        return

    if session:
        _show_session_detail(console, logs, session)
    elif tail:
        _live_tail(console, logs)
    else:
        _show_sessions_table(console, logs)


# ------------------------------------------------------------------
# Session list
# ------------------------------------------------------------------


def _show_sessions_table(console: Console, logs: Path) -> None:
    files = sorted(logs.glob("*.jsonl"))
    if not files:
        console.print("[yellow]No sessions recorded yet.[/yellow]")
        return

    table = Table(title="Recorded Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Events", justify="right")
    table.add_column("First Event")
    table.add_column("Last Event")

    for path in files:
        events = _load_file(path)
        if not events:
            continue
        table.add_row(
            path.stem,
            str(len(events)),
            events[0].timestamp,
            events[-1].timestamp,
        )

    console.print(table)


# ------------------------------------------------------------------
# Session detail
# ------------------------------------------------------------------


def _show_session_detail(console: Console, logs: Path, session_id: str) -> None:
    path = logs / f"{session_id}.jsonl"
    if not path.exists():
        console.print(f"[red]Session '{session_id}' not found.[/red]")
        return

    events = _load_file(path)
    table = Table(title=f"Events for session [cyan]{session_id}[/cyan]")
    table.add_column("Timestamp")
    table.add_column("Type", style="magenta")
    table.add_column("Data")

    for ev in events:
        table.add_row(
            ev.timestamp,
            ev.event_type.value,
            json.dumps(ev.data, default=str)[:120],
        )

    console.print(table)


# ------------------------------------------------------------------
# Live tail
# ------------------------------------------------------------------


def _live_tail(console: Console, logs: Path) -> None:
    """Watch all JSONL files for new lines and render them in a live table."""
    console.print("[dim]Tailing events — press Ctrl+C to stop.[/dim]\n")

    # Track file positions so we only read new lines
    offsets: dict[Path, int] = {}
    recent: list[ObservabilityEvent] = []
    max_recent = 30

    def _build_table() -> Table:
        table = Table(title="Live Events (last 30)")
        table.add_column("Timestamp")
        table.add_column("Session", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Data")
        for ev in recent[-max_recent:]:
            table.add_row(
                ev.timestamp,
                ev.session_id,
                ev.event_type.value,
                json.dumps(ev.data, default=str)[:100],
            )
        return table

    try:
        with Live(_build_table(), console=console, refresh_per_second=2) as live:
            while True:
                changed = False
                for path in logs.glob("*.jsonl"):
                    offset = offsets.get(path, 0)
                    size = path.stat().st_size
                    if size > offset:
                        with path.open(encoding="utf-8") as fh:
                            fh.seek(offset)
                            for line in fh:
                                line = line.strip()
                                if line:
                                    ev = ObservabilityEvent.model_validate(
                                        json.loads(line)
                                    )
                                    recent.append(ev)
                                    changed = True
                        offsets[path] = size
                if changed:
                    recent[:] = recent[-max_recent:]
                    live.update(_build_table())
                time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _load_file(path: Path) -> list[ObservabilityEvent]:
    events: list[ObservabilityEvent] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(
                    ObservabilityEvent.model_validate(json.loads(line))
                )
    return events
