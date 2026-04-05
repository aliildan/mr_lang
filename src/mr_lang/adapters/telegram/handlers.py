"""Telegram bot command and message handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from telegram import Update
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from mr_lang.adapters.telegram.sessions import SessionManager
    from mr_lang.core.runner import AgentRunner

console = Console(stderr=True)

BOT_NAME = "mr-lang"

HELP_TEXT = (
    "Available commands:\n"
    "/start — Welcome message\n"
    "/help — Show this help\n"
    "/clear — Reset conversation history\n\n"
    "Send any text message to chat with the agent."
)


def _get_ids(update: Update) -> tuple[int, int]:
    """Extract chat_id and user_id from an update."""
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    user_id = update.effective_user.id  # type: ignore[union-attr]
    return chat_id, user_id


def make_start_handler(sessions: SessionManager):  # noqa: ANN201
    """Return a /start command handler."""

    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id, user_id = _get_ids(update)
        console.print(f"[dim]/start from chat={chat_id} user={user_id}[/dim]")
        await update.message.reply_text(  # type: ignore[union-attr]
            f"Hello! I'm {BOT_NAME}, your AI assistant.\n\n"
            "Send me a message and I'll do my best to help.\n"
            "Use /help to see available commands."
        )

    return start_command


def make_help_handler():  # noqa: ANN201
    """Return a /help command handler."""

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(HELP_TEXT)  # type: ignore[union-attr]

    return help_command


def make_clear_handler(sessions: SessionManager):  # noqa: ANN201
    """Return a /clear command handler that resets the session."""

    async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id, user_id = _get_ids(update)
        new_thread = sessions.reset(chat_id, user_id)
        console.print(
            f"[yellow]Session reset[/yellow] chat={chat_id} user={user_id} -> {new_thread}"
        )
        await update.message.reply_text(  # type: ignore[union-attr]
            "Conversation cleared. Starting fresh!"
        )

    return clear_command


def make_text_handler(runner: AgentRunner, sessions: SessionManager):  # noqa: ANN201
    """Return a handler for plain text messages."""

    async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id, user_id = _get_ids(update)
        text = update.message.text  # type: ignore[union-attr]
        thread_id = sessions.get_thread_id(chat_id, user_id)

        console.print(
            f"[cyan]Message[/cyan] chat={chat_id} user={user_id} "
            f"thread={thread_id}: {text[:80]}"
        )

        try:
            result = await runner.run(message=text, thread_id=thread_id)
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                content = last.content if hasattr(last, "content") else str(last)
                # Telegram messages have a 4096 char limit
                for i in range(0, len(content), 4096):
                    await update.message.reply_text(  # type: ignore[union-attr]
                        content[i : i + 4096]
                    )
            else:
                await update.message.reply_text(  # type: ignore[union-attr]
                    "I received your message but have no response."
                )
        except Exception as exc:
            console.print(f"[red]Error handling message:[/red] {exc}")
            await update.message.reply_text(  # type: ignore[union-attr]
                "Sorry, something went wrong while processing your message."
            )

    return text_message


def make_photo_handler(runner: AgentRunner, sessions: SessionManager):  # noqa: ANN201
    """Return a handler for photo messages."""

    async def photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id, user_id = _get_ids(update)
        thread_id = sessions.get_thread_id(chat_id, user_id)
        caption = update.message.caption or ""  # type: ignore[union-attr]

        console.print(
            f"[cyan]Photo[/cyan] chat={chat_id} user={user_id} "
            f"thread={thread_id} caption={caption[:40]}"
        )

        # Download photo (largest available size)
        photo = update.message.photo[-1]  # type: ignore[union-attr]
        photo_file = await context.bot.get_file(photo.file_id)
        file_path = photo_file.file_path

        message = (
            f"[The user sent a photo (file: {file_path}). "
            "Full vision support is not yet available, but the photo was received.]"
        )
        if caption:
            message += f"\nCaption: {caption}"

        try:
            result = await runner.run(message=message, thread_id=thread_id)
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                content = last.content if hasattr(last, "content") else str(last)
                for i in range(0, len(content), 4096):
                    await update.message.reply_text(  # type: ignore[union-attr]
                        content[i : i + 4096]
                    )
        except Exception as exc:
            console.print(f"[red]Error handling photo:[/red] {exc}")
            await update.message.reply_text(  # type: ignore[union-attr]
                "Sorry, something went wrong while processing your photo."
            )

    return photo_message
