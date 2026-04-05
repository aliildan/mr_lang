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
    sqlite_path: Path = Field(default=Path("mr_lang.db"), description="SQLite database path")
    postgres_url: str | None = Field(default=None, description="PostgreSQL connection URL")

    # LangSmith
    langsmith_api_key: str | None = Field(default=None, description="LangSmith API key")
    langsmith_tracing: bool = Field(default=False, description="Enable LangSmith tracing")
    langsmith_project: str = Field(default="mr-lang", description="LangSmith project name")

    # Server
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    # Telegram
    telegram_bot_token: str | None = Field(default=None, description="Telegram bot token")

    # Logging
    log_level: str = Field(default="INFO")
