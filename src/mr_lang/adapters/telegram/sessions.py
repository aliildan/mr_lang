"""Session management for Telegram conversations."""

from __future__ import annotations

import threading
from uuid import uuid4


class SessionManager:
    """Maps (chat_id, user_id) pairs to unique thread_id strings.

    Each Telegram user in each chat gets a persistent conversation thread.
    Calling ``reset`` creates a new thread_id for that pair.
    """

    def __init__(self) -> None:
        self._sessions: dict[tuple[int, int], str] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _make_thread_id(chat_id: int, user_id: int) -> str:
        return f"tg-{chat_id}-{user_id}"

    def get_thread_id(self, chat_id: int, user_id: int) -> str:
        """Return the current thread_id, creating one if needed."""
        key = (chat_id, user_id)
        with self._lock:
            if key not in self._sessions:
                self._sessions[key] = self._make_thread_id(chat_id, user_id)
            return self._sessions[key]

    def reset(self, chat_id: int, user_id: int) -> str:
        """Reset the session and return a new thread_id."""
        key = (chat_id, user_id)
        new_id = f"tg-{chat_id}-{user_id}-{uuid4().hex[:8]}"
        with self._lock:
            self._sessions[key] = new_id
        return new_id
