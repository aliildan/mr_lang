"""Event data models for the local observability system."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """Types of observability events."""

    MODEL_CALL_START = "model_call_start"
    MODEL_CALL_END = "model_call_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    ERROR = "error"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


class ObservabilityEvent(BaseModel):
    """A single observability event recorded during agent execution."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 timestamp",
    )
    event_type: EventType
    session_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class SessionStats(BaseModel):
    """Aggregated statistics for a single session."""

    messages_count: int = 0
    tool_calls_count: int = 0
    errors_count: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    model_calls_count: int = 0
