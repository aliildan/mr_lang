"""Workspace data models."""

from __future__ import annotations

from pydantic import BaseModel


class WorkspaceDefinition(BaseModel):
    """Parsed workspace from a directory of Markdown files."""

    path: str
    identity: str = ""
    soul: str = ""
    user: str = ""
    tools_doc: str = ""
    agents_doc: str = ""
