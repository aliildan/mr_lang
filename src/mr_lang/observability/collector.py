"""Thread-safe event collector that persists events to JSONL files."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mr_lang.observability.events import EventType, ObservabilityEvent, SessionStats


class EventCollector:
    """Collects observability events in-memory and writes them to per-session JSONL files.

    Each session gets its own file at ``<log_dir>/<session_id>.jsonl``.
    """

    def __init__(self, log_dir: str | Path = ".mr_lang/logs") -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._events: list[ObservabilityEvent] = []
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    async def record(self, event: ObservabilityEvent) -> None:
        """Append *event* to the in-memory list and flush it to disk."""
        async with self._lock:
            self._events.append(event)
            self._write_event(event)

    def _write_event(self, event: ObservabilityEvent) -> None:
        path = self._log_dir / f"{event.session_id}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_session_events(self, session_id: str) -> list[ObservabilityEvent]:
        """Return all events for *session_id*, preferring disk over memory."""
        path = self._log_dir / f"{session_id}.jsonl"
        if path.exists():
            return _load_events_from_file(path)
        async with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    async def get_session_stats(self, session_id: str) -> SessionStats:
        """Compute aggregate stats for *session_id*."""
        events = await self.get_session_events(session_id)
        stats = SessionStats()
        for ev in events:
            if ev.event_type == EventType.MODEL_CALL_START:
                stats.model_calls_count += 1
                stats.messages_count += ev.data.get("messages_count", 0)
            elif ev.event_type == EventType.MODEL_CALL_END:
                stats.total_tokens += ev.data.get("total_tokens", 0)
                stats.total_duration_ms += ev.data.get("duration_ms", 0.0)
                stats.tool_calls_count += ev.data.get("tool_calls_count", 0)
            elif ev.event_type == EventType.ERROR:
                stats.errors_count += 1
        return stats

    async def get_sessions(self) -> list[dict]:
        """List all known sessions with basic info."""
        sessions: list[dict] = []
        for path in sorted(self._log_dir.glob("*.jsonl")):
            session_id = path.stem
            events = _load_events_from_file(path)
            if not events:
                continue
            sessions.append(
                {
                    "session_id": session_id,
                    "event_count": len(events),
                    "first_event": events[0].timestamp,
                    "last_event": events[-1].timestamp,
                }
            )
        return sessions


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _load_events_from_file(path: Path) -> list[ObservabilityEvent]:
    events: list[ObservabilityEvent] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            events.append(ObservabilityEvent.model_validate(json.loads(line)))
    return events
