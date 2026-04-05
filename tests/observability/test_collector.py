"""Tests for EventCollector."""

from __future__ import annotations

import pytest

from mr_lang.observability.collector import EventCollector
from mr_lang.observability.events import EventType, ObservabilityEvent, SessionStats


@pytest.fixture
def collector(tmp_path):
    return EventCollector(log_dir=tmp_path / "logs")


def _make_event(
    event_type: EventType,
    session_id: str = "sess-1",
    data: dict | None = None,
) -> ObservabilityEvent:
    return ObservabilityEvent(
        event_type=event_type,
        session_id=session_id,
        data=data or {},
    )


@pytest.mark.asyncio
async def test_record_creates_jsonl_file(collector: EventCollector) -> None:
    event = _make_event(EventType.SESSION_START)
    await collector.record(event)

    files = list(collector._log_dir.glob("*.jsonl"))
    assert len(files) == 1
    assert files[0].name == "sess-1.jsonl"


@pytest.mark.asyncio
async def test_record_appends_events(collector: EventCollector) -> None:
    await collector.record(_make_event(EventType.SESSION_START))
    await collector.record(_make_event(EventType.MODEL_CALL_START, data={"messages_count": 3}))
    await collector.record(_make_event(EventType.MODEL_CALL_END, data={"total_tokens": 100}))

    events = await collector.get_session_events("sess-1")
    assert len(events) == 3
    assert events[0].event_type == EventType.SESSION_START
    assert events[2].data["total_tokens"] == 100


@pytest.mark.asyncio
async def test_get_session_events_empty(collector: EventCollector) -> None:
    events = await collector.get_session_events("nonexistent")
    assert events == []


@pytest.mark.asyncio
async def test_get_session_stats(collector: EventCollector) -> None:
    await collector.record(
        _make_event(EventType.MODEL_CALL_START, data={"messages_count": 2})
    )
    await collector.record(
        _make_event(
            EventType.MODEL_CALL_END,
            data={"total_tokens": 150, "duration_ms": 320.5, "tool_calls_count": 1},
        )
    )
    await collector.record(
        _make_event(EventType.MODEL_CALL_START, data={"messages_count": 4})
    )
    await collector.record(
        _make_event(
            EventType.MODEL_CALL_END,
            data={"total_tokens": 200, "duration_ms": 410.0, "tool_calls_count": 0},
        )
    )
    await collector.record(_make_event(EventType.ERROR, data={"error": "boom"}))

    stats = await collector.get_session_stats("sess-1")
    assert isinstance(stats, SessionStats)
    assert stats.model_calls_count == 2
    assert stats.messages_count == 6
    assert stats.total_tokens == 350
    assert stats.total_duration_ms == pytest.approx(730.5)
    assert stats.tool_calls_count == 1
    assert stats.errors_count == 1


@pytest.mark.asyncio
async def test_get_sessions(collector: EventCollector) -> None:
    await collector.record(_make_event(EventType.SESSION_START, session_id="a"))
    await collector.record(_make_event(EventType.SESSION_START, session_id="b"))
    await collector.record(_make_event(EventType.MODEL_CALL_START, session_id="b"))

    sessions = await collector.get_sessions()
    ids = [s["session_id"] for s in sessions]
    assert "a" in ids
    assert "b" in ids

    sess_b = next(s for s in sessions if s["session_id"] == "b")
    assert sess_b["event_count"] == 2


@pytest.mark.asyncio
async def test_multiple_sessions_isolated(collector: EventCollector) -> None:
    await collector.record(_make_event(EventType.SESSION_START, session_id="x"))
    await collector.record(_make_event(EventType.SESSION_START, session_id="y"))

    x_events = await collector.get_session_events("x")
    y_events = await collector.get_session_events("y")
    assert len(x_events) == 1
    assert len(y_events) == 1
    assert x_events[0].session_id == "x"
