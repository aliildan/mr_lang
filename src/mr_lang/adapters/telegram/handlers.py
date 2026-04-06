"""Telegram bot command and message handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from mr_lang.adapters.telegram.auth import AuthGuard
    from mr_lang.adapters.telegram.sessions import SessionManager
    from mr_lang.core.runner import AgentRunner
    from mr_lang.skills.schema import SkillDefinition

console = Console(stderr=True)

BOT_NAME = "mr-lang"
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

HELP_TEXT = (
    "Available commands:\n"
    "/start — Welcome message\n"
    "/help — Show this help\n"
    "/clear — Reset conversation history\n\n"
    "Send any text message to chat with the agent."
)

ADMIN_HELP_TEXT = (
    "\n\nAdmin commands:\n"
    "/invite — Generate a new invite code\n"
    "/allow <user_id> — Manually authorize a user\n"
    "/revoke <user_id> — Revoke a user's access\n"
    "/status — Show bot access info"
)

UNAUTHORIZED_TEXT = (
    "You don't have access to this bot.\n\n"
    "If you have an invite code, send it as a message to gain access."
)


def _get_ids(update: Update) -> tuple[int, int]:
    """Extract chat_id and user_id from an update."""
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    user_id = update.effective_user.id  # type: ignore[union-attr]
    return chat_id, user_id


async def _reply_markdown(update: Update, text: str) -> None:
    """Send a message with Markdown formatting, falling back to plain text.

    Telegram's Markdown parser is strict — unclosed formatting characters
    or special chars will cause the API to reject the entire message.
    We try Markdown first, then fall back to plain text on failure.
    """
    for i in range(0, len(text), TELEGRAM_MAX_MESSAGE_LENGTH):
        chunk = text[i : i + TELEGRAM_MAX_MESSAGE_LENGTH]
        try:
            await update.message.reply_text(  # type: ignore[union-attr]
                chunk, parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            await update.message.reply_text(chunk)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Auth-aware handler wrappers
# ---------------------------------------------------------------------------


def make_start_handler(sessions: SessionManager, guard: AuthGuard):  # noqa: ANN201
    """Return a /start command handler."""

    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id, user_id = _get_ids(update)
        console.print(f"[dim]/start from chat={chat_id} user={user_id}[/dim]")

        if not guard.is_authorized(user_id):
            if guard.mode == "invite":
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"Welcome! I'm {BOT_NAME}.\n\n"
                    "This bot requires an invite code.\n"
                    "Please send your invite code to get started."
                )
            else:
                await update.message.reply_text(UNAUTHORIZED_TEXT)  # type: ignore[union-attr]
            return

        await update.message.reply_text(  # type: ignore[union-attr]
            f"Hello! I'm {BOT_NAME}, your AI assistant.\n\n"
            "Send me a message and I'll do my best to help.\n"
            "Use /help to see available commands."
        )

    return start_command


def make_help_handler(  # noqa: ANN201
    guard: AuthGuard,
    skills: list[SkillDefinition] | None = None,
):
    """Return a /help command handler with dynamic skill listing."""

    def _build_help_text(is_admin: bool) -> str:
        lines = [
            "Available commands:",
            "/start — Welcome message",
            "/help — Show this help",
            "/clear — Reset conversation",
        ]
        if skills:
            lines.append("")
            lines.append("Skills:")
            for skill in skills:
                cmd = skill.name.replace("-", "_")
                emoji = f"{skill.emoji} " if skill.emoji else ""
                desc = skill.description or skill.name
                lines.append(f"/{cmd} — {emoji}{desc}")
        lines.append("")
        lines.append("Send any text message to chat with the agent.")
        if is_admin:
            lines.append(ADMIN_HELP_TEXT)
        return "\n".join(lines)

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _, user_id = _get_ids(update)
        if not guard.is_authorized(user_id):
            await update.message.reply_text(UNAUTHORIZED_TEXT)  # type: ignore[union-attr]
            return

        text = _build_help_text(guard.is_admin(user_id))
        await update.message.reply_text(text)  # type: ignore[union-attr]

    return help_command


def make_clear_handler(sessions: SessionManager, guard: AuthGuard):  # noqa: ANN201
    """Return a /clear command handler that resets the session."""

    async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id, user_id = _get_ids(update)
        if not guard.is_authorized(user_id):
            await update.message.reply_text(UNAUTHORIZED_TEXT)  # type: ignore[union-attr]
            return

        new_thread = sessions.reset(chat_id, user_id)
        console.print(
            f"[yellow]Session reset[/yellow] chat={chat_id} user={user_id} -> {new_thread}"
        )
        await update.message.reply_text(  # type: ignore[union-attr]
            "Conversation cleared. Starting fresh!"
        )

    return clear_command


# ---------------------------------------------------------------------------
# Admin commands
# ---------------------------------------------------------------------------


def make_invite_handler(guard: AuthGuard):  # noqa: ANN201
    """Return a /invite handler (admin only) that generates invite codes."""

    async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _, user_id = _get_ids(update)
        if not guard.is_admin(user_id):
            await update.message.reply_text(  # type: ignore[union-attr]
                "Only admins can generate invite codes."
            )
            return

        code = guard.generate_invite_code()
        await update.message.reply_text(  # type: ignore[union-attr]
            f"New invite code: `{code}`\n\nShare this with users to grant access.",
            parse_mode="Markdown",
        )

    return invite_command


def make_allow_handler(guard: AuthGuard):  # noqa: ANN201
    """Return a /allow handler (admin only) to manually authorize a user."""

    async def allow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _, user_id = _get_ids(update)
        if not guard.is_admin(user_id):
            await update.message.reply_text(  # type: ignore[union-attr]
                "Only admins can authorize users."
            )
            return

        args = context.args or []
        if not args:
            await update.message.reply_text(  # type: ignore[union-attr]
                "Usage: /allow <user_id>"
            )
            return

        try:
            target_id = int(args[0])
        except ValueError:
            await update.message.reply_text(  # type: ignore[union-attr]
                "Invalid user ID. Must be a number."
            )
            return

        guard.add_user(target_id)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"User {target_id} has been authorized."
        )

    return allow_command


def make_revoke_handler(guard: AuthGuard):  # noqa: ANN201
    """Return a /revoke handler (admin only) to remove a user's access."""

    async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _, user_id = _get_ids(update)
        if not guard.is_admin(user_id):
            await update.message.reply_text(  # type: ignore[union-attr]
                "Only admins can revoke access."
            )
            return

        args = context.args or []
        if not args:
            await update.message.reply_text(  # type: ignore[union-attr]
                "Usage: /revoke <user_id>"
            )
            return

        try:
            target_id = int(args[0])
        except ValueError:
            await update.message.reply_text(  # type: ignore[union-attr]
                "Invalid user ID. Must be a number."
            )
            return

        guard.remove_user(target_id)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"User {target_id} access revoked."
        )

    return revoke_command


def make_status_handler(guard: AuthGuard):  # noqa: ANN201
    """Return a /status handler (admin only) showing bot access info."""

    async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _, user_id = _get_ids(update)
        if not guard.is_admin(user_id):
            await update.message.reply_text(  # type: ignore[union-attr]
                "Only admins can view status."
            )
            return

        await update.message.reply_text(  # type: ignore[union-attr]
            f"Mode: {guard.mode}\n"
            f"Authorized users: {guard.authorized_count()}\n"
            f"Active invite codes: {len(guard.config.invite_codes)}"
        )

    return status_command


# ---------------------------------------------------------------------------
# Dynamic skill command handlers
# ---------------------------------------------------------------------------


def make_skill_handler(guard: AuthGuard, skill: SkillDefinition):  # noqa: ANN201
    """Return a handler for a dynamic skill command."""

    async def skill_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _, user_id = _get_ids(update)
        if not guard.is_authorized(user_id):
            await update.message.reply_text(UNAUTHORIZED_TEXT)  # type: ignore[union-attr]
            return

        emoji = f"{skill.emoji} " if skill.emoji else ""
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{emoji}{skill.name}\n{skill.description}\n\nSend me a message to use this skill."
        )

    return skill_command


# ---------------------------------------------------------------------------
# Message handlers (with auth + invite code redemption)
# ---------------------------------------------------------------------------


def make_text_handler(  # noqa: ANN201
    runner: AgentRunner, sessions: SessionManager, guard: AuthGuard
):
    """Return a handler for plain text messages."""

    async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id, user_id = _get_ids(update)
        text = update.message.text  # type: ignore[union-attr]

        # Check if this is an invite code attempt
        if not guard.is_authorized(user_id):
            if guard.mode == "invite" and guard.try_redeem_code(user_id, text.strip()):
                console.print(f"[green]User authorized via code[/green] user={user_id}")
                await update.message.reply_text(  # type: ignore[union-attr]
                    "Access granted! You can now chat with the bot.\n"
                    "Use /help to see available commands."
                )
                return

            await update.message.reply_text(UNAUTHORIZED_TEXT)  # type: ignore[union-attr]
            return

        thread_id = sessions.get_thread_id(chat_id, user_id)
        console.print(
            f"[cyan]Message[/cyan] chat={chat_id} user={user_id} thread={thread_id}: {text[:80]}"
        )

        try:
            result = await runner.run(message=text, thread_id=thread_id)
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                content = last.content if hasattr(last, "content") else str(last)
                await _reply_markdown(update, content)
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


def make_photo_handler(  # noqa: ANN201
    runner: AgentRunner, sessions: SessionManager, guard: AuthGuard
):
    """Return a handler for photo messages."""

    async def photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id, user_id = _get_ids(update)
        if not guard.is_authorized(user_id):
            await update.message.reply_text(UNAUTHORIZED_TEXT)  # type: ignore[union-attr]
            return

        thread_id = sessions.get_thread_id(chat_id, user_id)
        caption = update.message.caption or ""  # type: ignore[union-attr]

        console.print(
            f"[cyan]Photo[/cyan] chat={chat_id} user={user_id} "
            f"thread={thread_id} caption={caption[:40]}"
        )

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
                await _reply_markdown(update, content)
        except Exception as exc:
            console.print(f"[red]Error handling photo:[/red] {exc}")
            await update.message.reply_text(  # type: ignore[union-attr]
                "Sorry, something went wrong while processing your photo."
            )

    return photo_message
