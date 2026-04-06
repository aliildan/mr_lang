"""High-level agent runner wrapping the LangGraph compiled graph."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

if TYPE_CHECKING:
    from mr_lang.middleware.base import BaseMiddleware


class AgentRunner:
    """Run and stream agent conversations."""

    def __init__(
        self,
        graph: CompiledStateGraph,
        middleware: list[BaseMiddleware] | None = None,
    ) -> None:
        self.graph = graph
        self._middleware = middleware or []

    async def run(
        self,
        message: str,
        thread_id: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """Run the agent synchronously and return the final state."""
        thread_id = thread_id or str(uuid4())
        config = {"configurable": {"thread_id": thread_id}, **kwargs}

        for mw in self._middleware:
            await mw.before_run(message, thread_id)

        try:
            result = await self.graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config=config,
            )
        except Exception as e:
            for mw in self._middleware:
                await mw.on_error(message, thread_id, e)
            raise

        for mw in self._middleware:
            await mw.after_run(message, thread_id, result)

        return result

    async def stream(
        self,
        message: str,
        thread_id: str | None = None,
        stream_mode: str = "messages",
        **kwargs: Any,
    ) -> AsyncIterator:
        """Stream agent execution (chunk-level)."""
        thread_id = thread_id or str(uuid4())
        config = {"configurable": {"thread_id": thread_id}, **kwargs}
        async for chunk in self.graph.astream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode=stream_mode,
        ):
            yield chunk

    async def stream_tokens(
        self,
        message: str,
        thread_id: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream individual tokens from the model response.

        Uses LangGraph's ``astream_events`` to yield tokens as they arrive,
        enabling real-time output in CLI and adapters.
        """
        thread_id = thread_id or str(uuid4())
        config = {"configurable": {"thread_id": thread_id}, **kwargs}
        async for event in self.graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream" and event.get("data", {}).get("chunk"):
                chunk = event["data"]["chunk"]
                content = getattr(chunk, "content", "")
                if content:
                    yield content
