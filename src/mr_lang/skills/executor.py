"""Activate skills by injecting into system prompt and loading required tools."""

from __future__ import annotations

import os

from mr_lang.core.registry import ToolRegistry
from mr_lang.exceptions import SkillError
from mr_lang.skills.schema import SkillDefinition


def validate_skill_requirements(skill: SkillDefinition, tool_registry: ToolRegistry) -> None:
    """Check that all skill requirements are satisfied.

    Raises SkillError if any requirement is missing.
    """
    for env_var in skill.requires.env:
        if not os.environ.get(env_var):
            raise SkillError(f"Skill '{skill.name}' requires env var: {env_var}")

    for tool_name in skill.requires.tools:
        if tool_name not in tool_registry.names():
            raise SkillError(f"Skill '{skill.name}' requires tool: {tool_name}")


def skill_to_prompt_section(skill: SkillDefinition) -> str:
    """Convert a skill definition into a system prompt section."""
    if skill.emoji:
        header = f"## Active Skill: {skill.emoji} {skill.name}"
    else:
        header = f"## Active Skill: {skill.name}"
    return f"{header}\n\n{skill.body}"
