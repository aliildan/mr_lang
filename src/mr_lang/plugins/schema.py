"""Pydantic model for plugin manifests."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    """Describes a mr_lang plugin and its capabilities."""

    name: str = Field(..., description="Plugin name (kebab-case)")
    version: str = Field(default="0.1.0", description="Semantic version")
    description: str = Field(default="", description="Short description")
    author: str = Field(default="", description="Author name")

    # Paths (relative to the manifest file)
    workspace_dir: Path | None = Field(
        default=None, description="Path to workspace directory"
    )
    skills_dir: Path | None = Field(
        default=None, description="Path to skills directory"
    )
    tools_module: str | None = Field(
        default=None,
        description="Python module path for tools (e.g., 'herr_molly.tools')",
    )

    # MCP servers
    mcp_servers: list[str] = Field(
        default_factory=list, description="MCP server URLs to connect to"
    )

    # CLI extension
    cli_module: str | None = Field(
        default=None,
        description="Python module with additional Typer commands",
    )

    # Dependencies
    dependencies: list[str] = Field(
        default_factory=list, description="Pip packages needed by this plugin"
    )

    # Internal: resolved base path (set during loading)
    _base_path: Path | None = None

    @property
    def base_path(self) -> Path | None:
        return self._base_path

    @base_path.setter
    def base_path(self, value: Path) -> None:
        self._base_path = value

    def resolve_workspace(self) -> Path | None:
        """Return the absolute workspace path, resolved against base_path."""
        if self.workspace_dir is None or self._base_path is None:
            return None
        return (self._base_path / self.workspace_dir).resolve()

    def resolve_skills(self) -> Path | None:
        """Return the absolute skills path, resolved against base_path."""
        if self.skills_dir is None or self._base_path is None:
            return None
        return (self._base_path / self.skills_dir).resolve()
