"""Long-term memory store factory."""

from __future__ import annotations

from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from mr_lang.exceptions import ConfigError


def get_store(backend: str = "memory", **kwargs) -> BaseStore:
    """Create a store instance for long-term memory.

    Args:
        backend: Backend type (memory, postgres)
        **kwargs: Backend-specific options
    """
    if backend == "memory":
        return InMemoryStore()

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
