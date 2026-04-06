"""Framework configuration with layered resolution."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MrLangConfig(BaseSettings):
    """Global mr_lang configuration.

    Resolution order: defaults -> mr_lang.toml -> ~/.config/mr_lang/config.toml -> env -> CLI flags.
    """

    model_config = SettingsConfigDict(
        env_prefix="MR_LANG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Workspace
    workspace_dir: Path | None = Field(default=None, description="Path to workspace directory")

    # Model defaults
    default_provider: str = Field(default="ollama", description="Default model provider")
    default_model: str = Field(default="llama3", description="Default model name")
    ollama_base_url: str | None = Field(
        default=None,
        description="Ollama API base URL (for local or cloud instances)",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Memory
    memory_backend: str = Field(
        default="memory", description="Checkpointer backend: memory, sqlite, postgres"
    )
    memory_enabled: bool = Field(
        default=True, description="Enable agent memory tools (remember/recall/forget)"
    )
    sqlite_path: Path = Field(default=Path("mr_lang.db"), description="SQLite database path")
    postgres_url: str | None = Field(
        default=None, description="PostgreSQL connection URL", repr=False
    )

    # Embeddings (for semantic memory search)
    embedding_provider: str = Field(
        default="ollama", description="Embedding provider: ollama, openai"
    )
    embedding_model: str = Field(default="nomic-embed-text", description="Embedding model name")

    # LangSmith
    langsmith_api_key: str | None = Field(default=None, description="LangSmith API key", repr=False)
    langsmith_tracing: bool = Field(default=False, description="Enable LangSmith tracing")
    langsmith_project: str = Field(default="mr-lang", description="LangSmith project name")

    # Server
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    # Telegram
    telegram_bot_token: str | None = Field(
        default=None, description="Telegram bot token", repr=False
    )
    telegram_auth_mode: str = Field(
        default="invite", description="Telegram auth mode: open, allowlist, invite"
    )
    telegram_admin_user_ids: str = Field(
        default="", description="Telegram admin user IDs (comma-separated)"
    )
    telegram_allowed_user_ids: str = Field(
        default="", description="Telegram pre-authorized user IDs (comma-separated)"
    )
    telegram_invite_codes: str = Field(
        default="", description="Telegram invite codes (comma-separated)"
    )
    telegram_max_uses_per_code: int = Field(
        default=0, description="Max uses per invite code (0 = unlimited)"
    )

    # Tool safety
    tools_allowed_paths: str = Field(
        default="",
        description="Comma-separated allowed filesystem paths (empty = allow all)",
    )
    tools_blocked_commands: str = Field(
        default="rm -rf /,mkfs,dd if=,:(){ :|:& };:",
        description="Comma-separated blocked shell command patterns",
    )

    def get_tools_allowed_paths(self) -> list[Path]:
        """Parse comma-separated allowed paths."""
        return [Path(x.strip()).resolve() for x in self.tools_allowed_paths.split(",") if x.strip()]

    def get_tools_blocked_commands(self) -> list[str]:
        """Parse comma-separated blocked command patterns."""
        return [x.strip() for x in self.tools_blocked_commands.split(",") if x.strip()]

    # Logging
    log_level: str = Field(default="INFO")

    def get_telegram_admin_user_ids(self) -> list[int]:
        """Parse comma-separated admin user IDs."""
        return self._safe_parse_ids(self.telegram_admin_user_ids)

    def get_telegram_allowed_user_ids(self) -> list[int]:
        """Parse comma-separated allowed user IDs."""
        return self._safe_parse_ids(self.telegram_allowed_user_ids)

    @staticmethod
    def _safe_parse_ids(raw: str) -> list[int]:
        """Parse comma-separated integers, warning on non-numeric values."""
        import logging

        result: list[int] = []
        for x in raw.split(","):
            x = x.strip()
            if not x:
                continue
            try:
                result.append(int(x))
            except ValueError:
                logging.getLogger(__name__).warning("Ignoring non-numeric user ID: %r", x)
        return result

    def get_telegram_invite_codes(self) -> list[str]:
        """Parse comma-separated invite codes."""
        return [x.strip() for x in self.telegram_invite_codes.split(",") if x.strip()]
