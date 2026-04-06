"""Telegram bot adapter for mr_lang."""

from __future__ import annotations

from mr_lang.adapters.telegram.auth import AuthConfig, AuthGuard
from mr_lang.adapters.telegram.bot import TelegramBot

__all__ = ["AuthConfig", "AuthGuard", "TelegramBot"]
