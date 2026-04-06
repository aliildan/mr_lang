"""Memory tools — give the agent the ability to remember and recall facts."""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool, tool
from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)

_EMBED_WARNING = (
    "Embedding model not available — memory saved without semantic search. "
    "Run 'ollama pull nomic-embed-text' to enable semantic recall."
)


def create_memory_tools(
    store: BaseStore,
    namespace_prefix: tuple[str, ...] = ("default",),
) -> list[BaseTool]:
    """Create memory tools bound to a specific store and namespace.

    The namespace_prefix is hardcoded at registration time so the LLM
    cannot escape its plugin's namespace.
    """
    _warned = False

    def _warn_once() -> None:
        nonlocal _warned
        if not _warned:
            logger.warning(_EMBED_WARNING)
            _warned = True

    @tool
    async def remember_fact(key: str, fact: str) -> str:
        """Store a fact for future reference.

        Use a descriptive key (e.g., 'user_name', 'preference_language').
        The fact should be a concise statement.
        """
        namespace = (*namespace_prefix, "facts")
        try:
            await store.aput(namespace, key, {"text": fact}, index=["text"])
        except Exception:
            _warn_once()
            await store.aput(namespace, key, {"text": fact})
        return f"Remembered: {key} = {fact}"

    @tool
    async def recall_facts(query: str) -> str:
        """Search memory for relevant facts.

        Use a natural language query describing what you're looking for.
        """
        namespace = (*namespace_prefix, "facts")
        try:
            results = await store.asearch(namespace, query=query, limit=5)
        except Exception:
            _warn_once()
            results = await store.asearch(namespace, limit=10)
        if not results:
            return "No relevant facts found in memory."
        lines = []
        for r in results:
            lines.append(f"- [{r.key}] {r.value['text']}")
        return "\n".join(lines)

    @tool
    async def forget_fact(key: str) -> str:
        """Remove a stored fact by its key."""
        namespace = (*namespace_prefix, "facts")
        await store.adelete(namespace, key)
        return f"Forgot: {key}"

    return [remember_fact, recall_facts, forget_fact]
