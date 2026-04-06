"""Logging middleware — logs model calls with timing, tokens, and tool usage."""

from __future__ import annotations

import time

from langchain_core.messages import AIMessage, BaseMessage
from rich.console import Console

from mr_lang.core.state import AgentState
from mr_lang.middleware.base import BaseMiddleware

console = Console(stderr=True)


class LoggingMiddleware(BaseMiddleware):
    """Logs each model invocation with wall-clock timing, token counts, and tool calls."""

    def __init__(self) -> None:
        self._call_start: float = 0.0

    async def before_model(self, state: AgentState) -> AgentState:
        self._call_start = time.monotonic()
        msg_count = len(state.get("messages", []))
        console.print(
            f"[dim]▶ model call  messages={msg_count}[/dim]",
        )
        return state

    async def after_model(self, state: AgentState, response: BaseMessage) -> BaseMessage:
        elapsed = time.monotonic() - self._call_start
        parts: list[str] = [f"elapsed={elapsed:.2f}s"]

        # Token usage (provider-dependent; usually on response_metadata)
        usage = getattr(response, "usage_metadata", None)
        if usage:
            parts.append(
                f"tokens(in={usage.get('input_tokens', '?')} out={usage.get('output_tokens', '?')})"
            )

        # Tool calls
        if isinstance(response, AIMessage) and response.tool_calls:
            names = [tc["name"] for tc in response.tool_calls]
            parts.append(f"tools={names}")

        console.print(f"[dim]◀ model done  {' | '.join(parts)}[/dim]")
        return response
