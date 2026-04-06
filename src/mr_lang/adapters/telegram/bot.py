"""Telegram bot adapter for mr_lang."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from rich.console import Console
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from mr_lang.adapters.telegram.auth import AuthConfig, AuthGuard
from mr_lang.adapters.telegram.handlers import (
    make_allow_handler,
    make_clear_handler,
    make_document_handler,
    make_help_handler,
    make_invite_handler,
    make_photo_handler,
    make_revoke_handler,
    make_skill_handler,
    make_start_handler,
    make_status_handler,
    make_text_handler,
)
from mr_lang.adapters.telegram.sessions import SessionManager
from mr_lang.exceptions import AdapterError

if TYPE_CHECKING:
    from telegram.ext import Application

    from mr_lang.core.runner import AgentRunner
    from mr_lang.skills.schema import SkillDefinition

console = Console(stderr=True)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Async Telegram bot that bridges messages to an AgentRunner."""

    def __init__(
        self,
        runner: AgentRunner,
        token: str,
        auth_config: AuthConfig | None = None,
        skills: list[SkillDefinition] | None = None,
    ) -> None:
        if not token:
            raise AdapterError("Telegram bot token is required")
        self.runner = runner
        self.token = token
        self.sessions = SessionManager()
        self.guard = AuthGuard(config=auth_config or AuthConfig())
        self.skills = skills or []
        self._app: Application | None = None
        self._stop_event: asyncio.Event | None = None

    def _build_application(self) -> Application:
        """Build and configure the telegram Application."""
        app = ApplicationBuilder().token(self.token).build()

        # Command handlers
        app.add_handler(CommandHandler("start", make_start_handler(self.sessions, self.guard)))
        app.add_handler(CommandHandler("help", make_help_handler(self.guard, self.skills)))
        app.add_handler(CommandHandler("clear", make_clear_handler(self.sessions, self.guard)))

        # Admin command handlers
        app.add_handler(CommandHandler("invite", make_invite_handler(self.guard)))
        app.add_handler(CommandHandler("allow", make_allow_handler(self.guard)))
        app.add_handler(CommandHandler("revoke", make_revoke_handler(self.guard)))
        app.add_handler(CommandHandler("status", make_status_handler(self.guard)))

        # Dynamic skill command handlers
        for skill in self.skills:
            cmd_name = skill.name.replace("-", "_")
            app.add_handler(CommandHandler(cmd_name, make_skill_handler(self.guard, skill)))

        # Message handlers
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                make_text_handler(self.runner, self.sessions, self.guard),
            )
        )
        app.add_handler(
            MessageHandler(
                filters.PHOTO,
                make_photo_handler(self.runner, self.sessions, self.guard),
            )
        )
        app.add_handler(
            MessageHandler(
                filters.Document.ALL,
                make_document_handler(self.runner, self.sessions, self.guard),
            )
        )

        # Log any unhandled handler exceptions so they appear in journald
        async def _error_handler(update: object, context: object) -> None:
            exc = getattr(context, "error", None)
            logger.error("Telegram handler error (update=%s): %s", update, exc, exc_info=exc)

        app.add_error_handler(_error_handler)

        return app

    async def _clear_stale_sessions(self) -> None:
        """Force-clear any existing getUpdates sessions via raw API call."""
        import httpx

        url = f"https://api.telegram.org/bot{self.token}"
        async with httpx.AsyncClient(timeout=10) as client:
            # Delete webhook and drop pending updates
            await client.post(f"{url}/deleteWebhook", json={"drop_pending_updates": True})
            # Short getUpdates to terminate any stale long-poll
            await client.get(f"{url}/getUpdates", params={"limit": 1, "timeout": 0})
        console.print("[dim]Cleared stale Telegram sessions.[/dim]")

    async def _register_bot_commands(self) -> None:
        """Register commands with Telegram so they appear in the / menu."""
        from telegram import BotCommand

        commands = [
            BotCommand("start", "Welcome message"),
            BotCommand("help", "Show help and available skills"),
            BotCommand("clear", "Reset conversation"),
        ]
        for skill in self.skills:
            cmd_name = skill.name.replace("-", "_")
            desc = skill.description[:256] if skill.description else skill.name
            commands.append(BotCommand(cmd_name, desc))

        await self._app.bot.set_my_commands(commands)  # type: ignore[union-attr]
        if self.skills:
            console.print(f"[green]Registered {len(self.skills)} skill command(s)[/green]")

    async def start(self) -> None:
        """Build the application, register handlers, and run polling."""
        console.print("[green]Starting Telegram bot...[/green]")

        await self._clear_stale_sessions()
        self._app = self._build_application()

        try:
            await self._app.initialize()
            await self._app.start()
            await self._register_bot_commands()
            console.print("[green]Telegram bot is running. Press Ctrl+C to stop.[/green]")
            await self._app.updater.start_polling(  # type: ignore[union-attr]
                drop_pending_updates=True,
            )

            # Block until stop() sets the event or the task is cancelled
            self._stop_event = asyncio.Event()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stop_event.wait()
        except Exception as exc:
            raise AdapterError(f"Telegram bot failed: {exc}") from exc

    async def stop(self) -> None:
        """Gracefully shut down the bot."""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._app is not None:
            console.print("[yellow]Stopping Telegram bot...[/yellow]")
            if self._app.updater and self._app.updater.running:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            console.print("[dim]Telegram bot stopped.[/dim]")
