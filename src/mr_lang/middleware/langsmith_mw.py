"""LangSmith middleware — configures environment for LangSmith tracing."""

from __future__ import annotations

import os

from langchain_core.messages import BaseMessage

from mr_lang.config import MrLangConfig
from mr_lang.core.state import AgentState
from mr_lang.middleware.base import BaseMiddleware


class LangSmithMiddleware(BaseMiddleware):
    """One-time setup middleware that sets LangSmith env vars from config.

    Reads ``langsmith_tracing``, ``langsmith_api_key``, and
    ``langsmith_project`` from :class:`MrLangConfig` and exports the
    corresponding environment variables on the first ``before_model`` call.
    """

    def __init__(self, config: MrLangConfig) -> None:
        self._config = config
        self._applied = False

    async def before_model(self, state: AgentState) -> AgentState:
        if self._applied:
            return state

        if self._config.langsmith_tracing:
            os.environ["LANGSMITH_TRACING"] = "true"
        else:
            os.environ["LANGSMITH_TRACING"] = "false"

        if self._config.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = self._config.langsmith_api_key

        os.environ["LANGSMITH_PROJECT"] = self._config.langsmith_project

        self._applied = True
        return state

    async def after_model(self, state: AgentState, response: BaseMessage) -> BaseMessage:
        return response
