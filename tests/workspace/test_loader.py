"""Tests for workspace loader."""

import pytest

from mr_lang.exceptions import WorkspaceError
from mr_lang.workspace.builder import build_system_prompt
from mr_lang.workspace.loader import load_workspace


def test_load_workspace(tmp_workspace):
    ws = load_workspace(tmp_workspace)
    assert "Test Agent" in ws.identity
    assert "helpful" in ws.soul


def test_load_workspace_missing_dir():
    with pytest.raises(WorkspaceError, match="not found"):
        load_workspace("/nonexistent/path")


def test_load_workspace_missing_identity(tmp_path):
    ws_dir = tmp_path / "empty_ws"
    ws_dir.mkdir()
    with pytest.raises(WorkspaceError, match="IDENTITY.md is required"):
        load_workspace(ws_dir)


def test_build_system_prompt(tmp_workspace):
    ws = load_workspace(tmp_workspace)
    prompt = build_system_prompt(ws)
    assert "Test Agent" in prompt
    assert "helpful" in prompt
