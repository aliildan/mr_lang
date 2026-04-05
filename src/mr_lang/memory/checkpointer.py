"""Checkpointer factory for short-term memory."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from mr_lang.exceptions import ConfigError


def get_checkpointer(backend: str = "memory", **kwargs) -> BaseCheckpointSaver:
    """Create a checkpointer instance.

    Args:
        backend: Backend type (memory, sqlite, postgres)
        **kwargs: Backend-specific options (e.g., path for sqlite, url for postgres)
    """
    if backend == "memory":
        return MemorySaver()

    if backend == "sqlite":
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        except ImportError as err:
            raise ConfigError("Install langgraph-checkpoint-sqlite for SQLite support") from err
        path = kwargs.get("path", "mr_lang.db")
        return AsyncSqliteSaver.from_conn_string(str(path))

    if backend == "postgres":
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError as err:
            raise ConfigError(
                "Install langgraph-checkpoint-postgres: pip install mr-lang[postgres]"
            ) from err
        url = kwargs.get("url")
        if not url:
            raise ConfigError("PostgreSQL URL required for postgres backend")
        return AsyncPostgresSaver.from_conn_string(url)

    raise ConfigError(f"Unknown checkpointer backend: {backend}")
