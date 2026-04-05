"""Observability middleware — records model call events to the EventCollector."""

from __future__ import annotations

import time

from langchain_core.messages import AIMessage, BaseMessage

from mr_lang.core.state import AgentState
from mr_lang.middleware.base import BaseMiddleware
from mr_lang.observability.collector import EventCollector
from mr_lang.observability.events import EventType, ObservabilityEvent


class ObservabilityMiddleware(BaseMiddleware):
    """Records ``model_call_start`` / ``model_call_end`` events for every model invocation."""

    def __init__(
        self,
        collector: EventCollector,
        session_id: str = "unknown",
    ) -> None:
        self._collector = collector
        self._session_id = session_id
        self._call_start: float = 0.0

    async def before_model(self, state: AgentState) -> AgentState:
        self._call_start = time.monotonic()
        msg_count = len(state.get("messages", []))
        tools = [
            t.name
            for t in state.get("metadata", {}).get("active_tools", [])
        ] if state.get("metadata", {}).get("active_tools") else []

        event = ObservabilityEvent(
            event_type=EventType.MODEL_CALL_START,
            session_id=self._session_id,
            data={"messages_count": msg_count, "active_tools": tools},
        )
        await self._collector.record(event)
        return state

    async def after_model(
        self, state: AgentState, response: BaseMessage
    ) -> BaseMessage:
        elapsed_ms = (time.monotonic() - self._call_start) * 1000

        total_tokens = 0
        usage = getattr(response, "usage_metadata", None)
        if usage:
            total_tokens = usage.get("input_tokens", 0) + usage.get(
                "output_tokens", 0
            )

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
