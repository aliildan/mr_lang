"""Load workspace Markdown files into a WorkspaceDefinition."""

from __future__ import annotations

from pathlib import Path

from mr_lang.exceptions import WorkspaceError
from mr_lang.workspace.schema import WorkspaceDefinition

_WORKSPACE_FILES = {
    "IDENTITY.md": "identity",
    "SOUL.md": "soul",
    "USER.md": "user",
    "TOOLS.md": "tools_doc",
    "AGENTS.md": "agents_doc",
}


def load_workspace(workspace_dir: str | Path) -> WorkspaceDefinition:
    """Load all workspace Markdown files from a directory.

    Args:
        workspace_dir: Path to workspace directory containing IDENTITY.md, SOUL.md, etc.

    Returns:
        Populated WorkspaceDefinition
    """
    workspace_dir = Path(workspace_dir)
    if not workspace_dir.is_dir():
        raise WorkspaceError(f"Workspace directory not found: {workspace_dir}")

    data: dict[str, str] = {"path": str(workspace_dir)}

    for filename, field in _WORKSPACE_FILES.items():
        filepath = workspace_dir / filename
        if filepath.exists():
            data[field] = filepath.read_text(encoding="utf-8").strip()

    if not data.get("identity"):
        raise WorkspaceError(f"IDENTITY.md is required in workspace: {workspace_dir}")

    return WorkspaceDefinition(**data)
