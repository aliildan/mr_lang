"""Skill definition data models."""

from __future__ import annotations

from pydantic import BaseModel


class SkillRequirements(BaseModel):
    """What a skill needs to function."""

    env: list[str] = []
    tools: list[str] = []
    config: list[str] = []


class SkillDefinition(BaseModel):
    """Parsed skill from a SKILL.md file."""

    name: str
    description: str = ""
    emoji: str = ""
    requires: SkillRequirements = SkillRequirements()
    tags: list[str] = []
    body: str = ""
    source_path: str = ""
