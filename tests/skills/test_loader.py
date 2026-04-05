"""Tests for skill loader."""

import pytest

from mr_lang.exceptions import SkillError
from mr_lang.skills.loader import load_skill, load_skills_dir


def test_load_skill(tmp_skill):
    skill = load_skill(tmp_skill)
    assert skill.name == "test-skill"
    assert skill.description == "A test skill"
    assert "test" in skill.tags
    assert "Test Skill" in skill.body


def test_load_skill_missing_file():
    with pytest.raises(SkillError, match="not found"):
        load_skill("/nonexistent/test.SKILL.md")


def test_load_skill_wrong_extension(tmp_path):
    bad = tmp_path / "test.md"
    bad.write_text("---\nname: bad\n---\nContent")
    with pytest.raises(SkillError, match="SKILL.md"):
        load_skill(bad)


def test_load_skills_dir(tmp_path):
    skill = tmp_path / "example.SKILL.md"
    skill.write_text("---\nname: example\ndescription: Example\n---\n\nBody")
    skills = load_skills_dir(tmp_path)
    assert len(skills) == 1
    assert skills[0].name == "example"


def test_load_skills_dir_empty(tmp_path):
    skills = load_skills_dir(tmp_path)
    assert skills == []
