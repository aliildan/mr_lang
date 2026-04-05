"""Load SKILL.md files into SkillDefinition models."""

from __future__ import annotations

from pathlib import Path

import frontmatter

from mr_lang.exceptions import SkillError
from mr_lang.skills.schema import SkillDefinition, SkillRequirements


def load_skill(path: str | Path) -> SkillDefinition:
    """Load a single SKILL.md file.

    Args:
        path: Path to a .SKILL.md file

    Returns:
        Parsed SkillDefinition
    """
    path = Path(path)
    if not path.exists():
        raise SkillError(f"Skill file not found: {path}")
    if not path.name.endswith(".SKILL.md"):
        raise SkillError(f"Skill file must end with .SKILL.md: {path}")

    post = frontmatter.load(str(path))
    metadata = post.metadata

    requires_data = metadata.get("requires", {})
    requires = SkillRequirements(
        env=requires_data.get("env", []),
        tools=requires_data.get("tools", []),
        config=requires_data.get("config", []),
    )

    return SkillDefinition(
        name=metadata.get("name", path.stem.replace(".SKILL", "")),
        description=metadata.get("description", ""),
        emoji=metadata.get("emoji", ""),
        requires=requires,
        tags=metadata.get("tags", []),
        body=post.content,
        source_path=str(path),
    )


def load_skills_dir(skills_dir: str | Path) -> list[SkillDefinition]:
    """Load all SKILL.md files from a directory.

    Args:
        skills_dir: Path to directory containing .SKILL.md files

    Returns:
        List of parsed SkillDefinitions
    """
    skills_dir = Path(skills_dir)
    if not skills_dir.is_dir():
        return []

    skills = []
    for path in sorted(skills_dir.rglob("*.SKILL.md")):
        skills.append(load_skill(path))
    return skills
