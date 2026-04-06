"""Observability middleware — records model call events to the EventCollector."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from mr_lang.core.state import AgentState
from mr_lang.middleware.base import BaseMiddleware
from mr_lang.observability.collector import EventCollector
from mr_lang.observability.events import EventType, ObservabilityEvent


class ObservabilityMiddleware(BaseMiddleware):
    """Records observability events for model calls, sessions, and errors."""

    def __init__(
        self,
        collector: EventCollector,
        session_id: str = "unknown",
    ) -> None:
        self._collector = collector
        self._session_id = session_id
        self._call_start: float = 0.0
        self._tool_start: float = 0.0
        self._run_start: float = 0.0

    async def before_model(self, state: AgentState) -> AgentState:
        self._call_start = time.monotonic()
        msg_count = len(state.get("messages", []))
        active_tools = state.get("metadata", {}).get("active_tools", [])
        tools = [t.name for t in active_tools] if active_tools else []

        event = ObservabilityEvent(
            event_type=EventType.MODEL_CALL_START,
            session_id=self._session_id,
            data={"messages_count": msg_count, "active_tools": tools},
        )
        await self._collector.record(event)
        return state

    async def after_model(self, state: AgentState, response: BaseMessage) -> BaseMessage:
        elapsed_ms = (time.monotonic() - self._call_start) * 1000

        total_tokens = 0
        usage = getattr(response, "usage_metadata", None)
        if usage:
            total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

        tool_calls_count = 0
        tool_names: list[str] = []
        if isinstance(response, AIMessage) and response.tool_calls:
            tool_calls_count = len(response.tool_calls)
            tool_names = [tc["name"] for tc in response.tool_calls]

        event = ObservabilityEvent(
            event_type=EventType.MODEL_CALL_END,
            session_id=self._session_id,
            data={
                "duration_ms": round(elapsed_ms, 2),
                "total_tokens": total_tokens,
                "tool_calls_count": tool_calls_count,
                "tool_names": tool_names,
            },
        )
        await self._collector.record(event)
        return response

    async def before_tool(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        self._tool_start = time.monotonic()
        event = ObservabilityEvent(
            event_type=EventType.TOOL_CALL_START,
            session_id=self._session_id,
            data={"tool_name": tool_name},
        )
        await self._collector.record(event)

    async def after_tool(self, tool_name: str, tool_input: dict[str, Any], result: Any) -> None:
        elapsed_ms = (time.monotonic() - self._tool_start) * 1000
        event = ObservabilityEvent(
            event_type=EventType.TOOL_CALL_END,
            session_id=self._session_id,
            data={
                "tool_name": tool_name,
                "duration_ms": round(elapsed_ms, 2),
            },
        )
        await self._collector.record(event)

    async def before_run(self, message: str, thread_id: str) -> None:
        self._run_start = time.monotonic()
        self._session_id = thread_id
        event = ObservabilityEvent(
            event_type=EventType.SESSION_START,
            session_id=thread_id,
            data={"message_length": len(message)},
        )
        await self._collector.record(event)

    async def after_run(self, message: str, thread_id: str, result: dict[str, Any]) -> None:
        elapsed_ms = (time.monotonic() - self._run_start) * 1000
        msg_count = len(result.get("messages", []))
        event = ObservabilityEvent(
            event_type=EventType.SESSION_END,
            session_id=thread_id,
            data={
                "duration_ms": round(elapsed_ms, 2),
                "messages_count": msg_count,
            },
        )
        await self._collector.record(event)

    async def on_error(self, message: str, thread_id: str, error: Exception) -> None:
        event = ObservabilityEvent(
            event_type=EventType.ERROR,
            session_id=thread_id,
            data={
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )
        await self._collector.record(event)
