"""Telegram bot adapter for mr_lang."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from mr_lang.adapters.telegram.handlers import (
    make_clear_handler,
    make_help_handler,
    make_photo_handler,
    make_start_handler,
    make_text_handler,
)
from mr_lang.adapters.telegram.sessions import SessionManager
from mr_lang.exceptions import AdapterError

if TYPE_CHECKING:
    from telegram.ext import Application

    from mr_lang.core.runner import AgentRunner

console = Console(stderr=True)


class TelegramBot:
    """Async Telegram bot that bridges messages to an AgentRunner."""

    def __init__(self, runner: AgentRunner, token: str) -> None:
        if not token:
            raise AdapterError("Telegram bot token is required")
        self.runner = runner
        self.token = token
        self.sessions = SessionManager()
        self._app: Application | None = None

    def _build_application(self) -> Application:
        """Build and configure the telegram Application."""
        app = ApplicationBuilder().token(self.token).build()

        # Command handlers
        app.add_handler(CommandHandler("start", make_start_handler(self.sessions)))
        app.add_handler(CommandHandler("help", make_help_handler()))
        app.add_handler(CommandHandler("clear", make_clear_handler(self.sessions)))

        # Message handlers
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                make_text_handler(self.runner, self.sessions),
            )
        )
        app.add_handler(
            MessageHandler(
                filters.PHOTO,
                make_photo_handler(self.runner, self.sessions),
            )
        )

        return app

    async def start(self) -> None:
        """Build the application, register handlers, and run polling."""
        console.print("[green]Starting Telegram bot...[/green]")
        self._app = self._build_application()

        try:
            await self._app.initialize()
            await self._app.start()
            console.print("[green]Telegram bot is running. Press Ctrl+C to stop.[/green]")
            await self._app.updater.start_polling()  # type: ignore[union-attr]

            # Block until stop() is called or a signal is received
            import asyncio
            import contextlib

            stop_event = asyncio.Event()
            with contextlib.suppress(asyncio.CancelledError):
                await stop_event.wait()
        except Exception as exc:
            raise AdapterError(f"Telegram bot failed: {exc}") from exc

    async def stop(self) -> None:
        """Gracefully shut down the bot."""
        if self._app is not None:
            console.print("[yellow]Stopping Telegram bot...[/yellow]")
            if self._app.updater and self._app.updater.running:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            console.print("[dim]Telegram bot stopped.[/dim]")
