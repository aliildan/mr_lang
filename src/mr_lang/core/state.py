"""Agent state definitions for LangGraph."""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Core state for all mr_lang agents.

    Uses LangGraph's add_messages reducer for the messages key,
    which handles appending, updating by ID, and deduplication.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    workspace: dict[str, Any]
    active_skills: list[str]
    metadata: dict[str, Any]
