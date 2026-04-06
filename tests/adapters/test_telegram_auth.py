"""Tests for Telegram bot access control (AuthGuard)."""

from __future__ import annotations

from mr_lang.adapters.telegram.auth import AuthConfig, AuthGuard


class TestAuthGuardOpenMode:
    def test_open_mode_authorizes_anyone(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="open"))
        assert guard.is_authorized(12345)

    def test_open_mode_redeem_always_succeeds(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="open"))
        assert guard.try_redeem_code(1, "anything")


class TestAuthGuardAllowlistMode:
    def test_allowed_user_is_authorized(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="allowlist", allowed_user_ids=[42]))
        assert guard.is_authorized(42)

    def test_unknown_user_is_rejected(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="allowlist", allowed_user_ids=[42]))
        assert not guard.is_authorized(99)

    def test_admin_is_authorized(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="allowlist", admin_user_ids=[10]))
        assert guard.is_authorized(10)


class TestAuthGuardInviteMode:
    def test_unauthorized_user_rejected(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="invite"))
        assert not guard.is_authorized(1)

    def test_redeem_valid_code(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="invite", invite_codes=["abc123"]))
        assert guard.try_redeem_code(1, "abc123")
        assert guard.is_authorized(1)

    def test_redeem_invalid_code(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="invite", invite_codes=["abc123"]))
        assert not guard.try_redeem_code(1, "wrong")
        assert not guard.is_authorized(1)

    def test_already_authorized_user_returns_true(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="invite", allowed_user_ids=[42]))
        assert guard.try_redeem_code(42, "irrelevant")

    def test_max_uses_per_code(self) -> None:
        guard = AuthGuard(
            config=AuthConfig(mode="invite", invite_codes=["code1"], max_uses_per_code=2)
        )
        assert guard.try_redeem_code(1, "code1")
        assert guard.try_redeem_code(2, "code1")
        assert not guard.try_redeem_code(3, "code1")

    def test_unlimited_uses_when_zero(self) -> None:
        guard = AuthGuard(
            config=AuthConfig(mode="invite", invite_codes=["code1"], max_uses_per_code=0)
        )
        for i in range(20):
            assert guard.try_redeem_code(i, "code1")


class TestAuthGuardAdmin:
    def test_is_admin(self) -> None:
        guard = AuthGuard(config=AuthConfig(admin_user_ids=[10]))
        assert guard.is_admin(10)
        assert not guard.is_admin(99)

    def test_add_user(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="allowlist"))
        assert not guard.is_authorized(50)
        guard.add_user(50)
        assert guard.is_authorized(50)

    def test_remove_user(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="allowlist", allowed_user_ids=[42]))
        assert guard.is_authorized(42)
        guard.remove_user(42)
        assert not guard.is_authorized(42)

    def test_remove_nonexistent_user_no_error(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="allowlist"))
        guard.remove_user(999)  # should not raise

    def test_generate_invite_code(self) -> None:
        guard = AuthGuard(config=AuthConfig(mode="invite"))
        code = guard.generate_invite_code()
        assert code in guard.config.invite_codes
        assert guard.try_redeem_code(1, code)

    def test_authorized_count(self) -> None:
        guard = AuthGuard(
            config=AuthConfig(mode="invite", allowed_user_ids=[1, 2], admin_user_ids=[3])
        )
        assert guard.authorized_count() == 3
        guard.add_user(4)
        assert guard.authorized_count() == 4
