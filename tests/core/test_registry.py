"""Tests for tool and skill registries."""

import pytest
from langchain_core.tools import tool

from mr_lang.core.registry import ToolRegistry
from mr_lang.exceptions import ToolError


@tool
def dummy_tool(x: str) -> str:
    """A dummy tool for testing."""
    return x


def test_register_and_get():
    registry = ToolRegistry()
    registry.register(dummy_tool)
    assert registry.get("dummy_tool") is dummy_tool


def test_list_tools():
    registry = ToolRegistry()
    registry.register(dummy_tool)
    assert len(registry) == 1
    assert "dummy_tool" in registry.names()


def test_duplicate_raises():
    registry = ToolRegistry()
    registry.register(dummy_tool)
    with pytest.raises(ToolError, match="already registered"):
        registry.register(dummy_tool)


def test_get_missing_raises():
    registry = ToolRegistry()
    with pytest.raises(ToolError, match="not found"):
        registry.get("nonexistent")
