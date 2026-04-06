"""Logging middleware — logs model calls with timing, tokens, and tool usage."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage
from rich.console import Console

from mr_lang.core.state import AgentState
from mr_lang.middleware.base import BaseMiddleware

console = Console(stderr=True)

_RESULT_PREVIEW_LEN = 200


class LoggingMiddleware(BaseMiddleware):
    """Logs each model invocation with wall-clock timing, token counts, and tool calls.

    When ``verbose=True``, also logs tool call arguments and result previews.
    """

    def __init__(self, verbose: bool = False) -> None:
        self._call_start: float = 0.0
        self._verbose = verbose

    async def before_model(self, state: AgentState) -> AgentState:
        self._call_start = time.monotonic()
        msg_count = len(state.get("messages", []))
        console.print(f"[dim]▶ model call  messages={msg_count}[/dim]")
        return state

    async def after_model(self, state: AgentState, response: BaseMessage) -> BaseMessage:
        elapsed = time.monotonic() - self._call_start
        parts: list[str] = [f"elapsed={elapsed:.2f}s"]

        usage = getattr(response, "usage_metadata", None)
        if usage:
            parts.append(
                f"tokens(in={usage.get('input_tokens', '?')} out={usage.get('output_tokens', '?')})"
            )

        if isinstance(response, AIMessage) and response.tool_calls:
            names = [tc["name"] for tc in response.tool_calls]
            parts.append(f"tools={names}")

        console.print(f"[dim]◀ model done  {' | '.join(parts)}[/dim]")
        return response

    async def before_tool(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        if not self._verbose:
            return
        args_str = "  ".join(f"{k}={repr(v)[:80]}" for k, v in tool_input.items())
        console.print(f"[dim cyan]  ▶ {tool_name}  {args_str}[/dim cyan]")

    async def after_tool(
        self, tool_name: str, tool_input: dict[str, Any], result: Any
    ) -> None:
        if not self._verbose:
            return
        if result is None:
            return
        result_str = str(result)
        preview = result_str[:_RESULT_PREVIEW_LEN]
        if len(result_str) > _RESULT_PREVIEW_LEN:
            preview += f"… (+{len(result_str) - _RESULT_PREVIEW_LEN} chars)"
        console.print(f"[dim green]  ◀ {tool_name}  {preview}[/dim green]")
