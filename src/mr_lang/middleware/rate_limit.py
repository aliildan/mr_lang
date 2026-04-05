"""Rate-limiting middleware using a token-bucket algorithm."""

from __future__ import annotations

import time

from langchain_core.messages import BaseMessage

from mr_lang.core.state import AgentState
from mr_lang.exceptions import MrLangError
from mr_lang.middleware.base import BaseMiddleware


class RateLimitExceededError(MrLangError):
    """Raised when the model call rate limit is exceeded."""


class RateLimitMiddleware(BaseMiddleware):
    """Limits model invocations per minute via a simple token bucket.

    Parameters
    ----------
    max_calls_per_minute:
        Maximum number of model calls allowed within a rolling 60-second window.
    """

    def __init__(self, max_calls_per_minute: int = 30) -> None:
        self._max_calls = max_calls_per_minute
        self._tokens = float(max_calls_per_minute)
        self._last_refill: float = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._max_calls,
            self._tokens + elapsed * (self._max_calls / 60.0),
        )
        self._last_refill = now

    async def before_model(self, state: AgentState) -> AgentState:
        self._refill()

        if self._tokens < 1.0:
            raise RateLimitExceededError(
                f"Rate limit exceeded: {self._max_calls} calls/min. "
                "Please wait before retrying."
            )

        self._tokens -= 1.0
        return state

    async def after_model(
        self, state: AgentState, response: BaseMessage
    ) -> BaseMessage:
        return response
