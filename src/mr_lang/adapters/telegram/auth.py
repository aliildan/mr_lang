"""Telegram bot access control.

Three modes:
- "open"      — anyone can use the bot (dev only)
- "allowlist" — only pre-approved user IDs can use the bot
- "invite"    — users must send a valid invite code to gain access

Modes can be combined: allowlist seeds permanent admins, invite lets
new users join with a code.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AuthConfig(BaseModel):
    """Configuration for Telegram access control."""

    mode: str = "invite"  # "open", "allowlist", "invite"
    allowed_user_ids: list[int] = []
    admin_user_ids: list[int] = []
    invite_codes: list[str] = []
    max_uses_per_code: int = 0  # 0 = unlimited


@dataclass
class AuthGuard:
    """Manages Telegram bot access control.

    Usage:
        guard = AuthGuard(config)
        if not guard.is_authorized(user_id):
            # reject
        if guard.try_redeem_code(user_id, code):
            # user is now authorized
    """

    config: AuthConfig
    _authorized_users: set[int] = field(default_factory=set)
    _code_uses: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Seed with allowlist and admin IDs
        self._authorized_users.update(self.config.allowed_user_ids)
        self._authorized_users.update(self.config.admin_user_ids)

    @property
    def mode(self) -> str:
        return self.config.mode

    def is_authorized(self, user_id: int) -> bool:
        """Check if a user is allowed to use the bot."""
        if self.config.mode == "open":
            return True
        return user_id in self._authorized_users

    def is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin."""
        return user_id in self.config.admin_user_ids

    def try_redeem_code(self, user_id: int, code: str) -> bool:
        """Attempt to redeem an invite code. Returns True if successful."""
        if self.config.mode == "open":
            return True

        if user_id in self._authorized_users:
            return True  # already authorized

        if code not in self.config.invite_codes:
            return False

        # Check max uses
        if self.config.max_uses_per_code > 0:
            uses = self._code_uses.get(code, 0)
            if uses >= self.config.max_uses_per_code:
                return False
            self._code_uses[code] = uses + 1

        self._authorized_users.add(user_id)
        logger.info("User %d authorized via invite code", user_id)
        return True

    def add_user(self, user_id: int) -> None:
        """Manually authorize a user (admin action)."""
        self._authorized_users.add(user_id)
        logger.info("User %d manually authorized", user_id)

    def remove_user(self, user_id: int) -> None:
        """Revoke a user's access (admin action)."""
        self._authorized_users.discard(user_id)
        logger.info("User %d access revoked", user_id)

    def generate_invite_code(self) -> str:
        """Generate and register a new invite code."""
        code = secrets.token_urlsafe(8)
        self.config.invite_codes.append(code)
        logger.info("Generated invite code: %s", code)
        return code

    def authorized_count(self) -> int:
        """Number of currently authorized users."""
        return len(self._authorized_users)
