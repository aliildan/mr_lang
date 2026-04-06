"""Middleware protocol for before/after model hooks."""

from __future__ import annotations

from typing import Any, Protocol

from langchain_core.messages import BaseMessage

from mr_lang.core.state import AgentState


class Middleware(Protocol):
    """Protocol for agent middleware.

    Middleware runs before and after each model invocation,
    allowing inspection, transformation, or side effects.
    """

    async def before_model(self, state: AgentState) -> AgentState:
        """Called before the model is invoked. Can modify state."""
        ...

    async def after_model(self, state: AgentState, response: BaseMessage) -> BaseMessage:
        """Called after the model responds. Can modify the response."""
        ...

    async def before_tool(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        """Called before a tool is executed."""
        ...

    async def after_tool(self, tool_name: str, tool_input: dict[str, Any], result: Any) -> None:
        """Called after a tool finishes."""
        ...

    async def before_run(self, message: str, thread_id: str) -> None:
        """Called before the agent run starts."""
        ...

    async def after_run(self, message: str, thread_id: str, result: dict[str, Any]) -> None:
        """Called after the agent run completes."""
        ...

    async def on_error(self, message: str, thread_id: str, error: Exception) -> None:
        """Called when an error occurs during the agent run."""
        ...


class BaseMiddleware:
    """Base class with no-op defaults for middleware."""

    async def before_model(self, state: AgentState) -> AgentState:
        return state

    async def after_model(self, state: AgentState, response: BaseMessage) -> BaseMessage:
        return response

    async def before_tool(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        pass

    async def after_tool(self, tool_name: str, tool_input: dict[str, Any], result: Any) -> None:
        pass

    async def before_run(self, message: str, thread_id: str) -> None:
        pass

    async def after_run(self, message: str, thread_id: str, result: dict[str, Any]) -> None:
        pass

    async def on_error(self, message: str, thread_id: str, error: Exception) -> None:
        pass
