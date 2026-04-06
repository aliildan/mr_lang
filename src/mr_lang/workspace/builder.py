"""Build system prompt from workspace definition."""

from __future__ import annotations

from mr_lang.workspace.schema import WorkspaceDefinition


def build_system_prompt(workspace: WorkspaceDefinition) -> str:
    """Assemble a system prompt from workspace Markdown files.

    Concatenates IDENTITY + SOUL + USER + TOOLS context into a single
    system message, with clear section separators.
    """
    sections: list[str] = []

    if workspace.identity:
        sections.append(workspace.identity)

    if workspace.soul:
        sections.append(workspace.soul)

    if workspace.user:
        sections.append(f"# Current User\n\n{workspace.user}")

    if workspace.tools_doc:
        sections.append(f"# Available Tools\n\n{workspace.tools_doc}")

    if workspace.agents_doc:
        sections.append(f"# Agents\n\n{workspace.agents_doc}")

    return "\n\n---\n\n".join(sections)
