"""High-level agent runner wrapping the LangGraph compiled graph."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langgraph.graph.graph import CompiledGraph


class AgentRunner:
    """Run and stream agent conversations."""

    def __init__(self, graph: CompiledGraph) -> None:
        self.graph = graph

    async def run(
        self,
        message: str,
        thread_id: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """Run the agent synchronously and return the final state."""
        thread_id = thread_id or str(uuid4())
        config = {"configurable": {"thread_id": thread_id}, **kwargs}
        result = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        return result

    async def stream(
        self,
        message: str,
        thread_id: str | None = None,
        stream_mode: str = "messages",
        **kwargs: Any,
    ) -> AsyncIterator:
        """Stream agent execution."""
        thread_id = thread_id or str(uuid4())
        config = {"configurable": {"thread_id": thread_id}, **kwargs}
        async for chunk in self.graph.astream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode=stream_mode,
        ):
            yield chunk
