"""Tests for the Telegram adapter SessionManager."""

from __future__ import annotations

from mr_lang.adapters.telegram.sessions import SessionManager


class TestSessionManager:
    """Tests for SessionManager."""

    def test_get_thread_id_creates_deterministic_id(self) -> None:
        sm = SessionManager()
        thread_id = sm.get_thread_id(chat_id=100, user_id=42)
        assert thread_id == "tg-100-42"

    def test_get_thread_id_returns_same_id_on_repeat(self) -> None:
        sm = SessionManager()
        first = sm.get_thread_id(chat_id=1, user_id=2)
        second = sm.get_thread_id(chat_id=1, user_id=2)
        assert first == second

    def test_different_users_get_different_threads(self) -> None:
        sm = SessionManager()
        t1 = sm.get_thread_id(chat_id=1, user_id=10)
        t2 = sm.get_thread_id(chat_id=1, user_id=20)
        assert t1 != t2

    def test_different_chats_get_different_threads(self) -> None:
        sm = SessionManager()
        t1 = sm.get_thread_id(chat_id=100, user_id=1)
        t2 = sm.get_thread_id(chat_id=200, user_id=1)
        assert t1 != t2

    def test_reset_changes_thread_id(self) -> None:
        sm = SessionManager()
        original = sm.get_thread_id(chat_id=1, user_id=1)
        new = sm.reset(chat_id=1, user_id=1)
        assert new != original
        assert new.startswith("tg-1-1-")

    def test_reset_returns_new_id_on_subsequent_get(self) -> None:
        sm = SessionManager()
        sm.get_thread_id(chat_id=5, user_id=5)
        new = sm.reset(chat_id=5, user_id=5)
        current = sm.get_thread_id(chat_id=5, user_id=5)
        assert current == new

    def test_reset_does_not_affect_other_sessions(self) -> None:
        sm = SessionManager()
        sm.get_thread_id(chat_id=1, user_id=1)
        t2_before = sm.get_thread_id(chat_id=2, user_id=2)
        sm.reset(chat_id=1, user_id=1)
        t2_after = sm.get_thread_id(chat_id=2, user_id=2)
        assert t2_before == t2_after

    def test_multiple_resets_produce_unique_ids(self) -> None:
        sm = SessionManager()
        ids = {sm.reset(chat_id=1, user_id=1) for _ in range(10)}
        assert len(ids) == 10
