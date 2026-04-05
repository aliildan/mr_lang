"""Middleware protocol for before/after model hooks."""

from __future__ import annotations

from typing import Protocol

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


class BaseMiddleware:
    """Base class with no-op defaults for middleware."""

    async def before_model(self, state: AgentState) -> AgentState:
        return state

    async def after_model(self, state: AgentState, response: BaseMessage) -> BaseMessage:
        return response
