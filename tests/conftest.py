"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Create a minimal temporary workspace directory."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "IDENTITY.md").write_text("# Identity\n\n- Name: Test Agent\n- Role: Testing")
    (ws / "SOUL.md").write_text("# Personality\n\nBe helpful and concise.")
    return ws


@pytest.fixture
def tmp_skill(tmp_path: Path) -> Path:
    """Create a temporary skill file."""
    skill = tmp_path / "test.SKILL.md"
    skill.write_text(
        "---\n"
        "name: test-skill\n"
        "description: A test skill\n"
        "emoji: '🧪'\n"
        "requires:\n"
        "  tools: []\n"
        "  env: []\n"
        "tags: [test]\n"
        "---\n\n"
        "# Test Skill\n\nDo the test thing.\n"
    )
    return skill
