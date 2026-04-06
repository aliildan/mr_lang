"""Long-term memory store factory."""

from __future__ import annotations

from typing import Any

from langchain_core.embeddings import Embeddings
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from mr_lang.exceptions import ConfigError


async def get_store(
    backend: str = "memory",
    embed: Embeddings | None = None,
    **kwargs: Any,
) -> BaseStore:
    """Create a store instance for long-term memory.

    Args:
        backend: Backend type (memory, sqlite, postgres)
        embed: Embeddings instance for semantic search (optional)
        **kwargs: Backend-specific options (e.g., path for sqlite, url for postgres)
    """
    index_config = None
    if embed is not None:
        index_config = {"dims": 768, "embed": embed}

    if backend == "memory":
        return InMemoryStore(index=index_config)

    if backend == "sqlite":
        try:
            import aiosqlite
            from langgraph.store.sqlite.aio import AsyncSqliteStore
        except ImportError as err:
            raise ConfigError(
                "Install langgraph-checkpoint-sqlite and aiosqlite for SQLite store support"
            ) from err
        path = kwargs.get("path", "mr_lang.db")
        conn = aiosqlite.connect(str(path), isolation_level=None)
        await conn  # open the connection
        store = AsyncSqliteStore(conn)
        await store.setup()
        return store

    if backend == "postgres":
        try:
            from langgraph.store.postgres import PostgresStore
        except ImportError as err:
            raise ConfigError(
                "Install langgraph with postgres: pip install mr-lang[postgres]"
            ) from err
        url = kwargs.get("url")
        if not url:
            raise ConfigError("PostgreSQL URL required for postgres store")
        return PostgresStore.from_conn_string(url)

    raise ConfigError(f"Unknown store backend: {backend}")
