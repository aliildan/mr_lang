"""Tests for the MCP server/client adapter."""

from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Patch langgraph before importing our modules (API changed across versions)
# ---------------------------------------------------------------------------
def _ensure_langgraph_importable() -> None:
    """Ensure langgraph.graph.graph can be imported even on newer langgraph."""
    try:
        from langgraph.graph.graph import CompiledGraph  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        mod = types.ModuleType("langgraph.graph.graph")
        mod.CompiledGraph = type("CompiledGraph", (), {})  # type: ignore[attr-defined]
        sys.modules["langgraph.graph.graph"] = mod


_ensure_langgraph_importable()

from mr_lang.adapters.mcp.server import McpServer  # noqa: E402
from mr_lang.core.registry import ToolRegistry  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DummyInput(BaseModel):
    query: str = Field(description="Search query")
    limit: int = Field(default=10, description="Max results")


def _make_dummy_tool(name: str = "search", description: str = "Search things") -> BaseTool:
    """Create a minimal LangChain tool for testing."""

    def _fn(query: str, limit: int = 10) -> str:
        return f"results for {query} (limit={limit})"

    return StructuredTool.from_function(
        func=_fn,
        name=name,
        description=description,
        args_schema=_DummyInput,
    )


def _make_runner_mock() -> MagicMock:
    """Return a mock AgentRunner whose run() returns a minimal result."""
    runner = MagicMock()
    msg = MagicMock()
    msg.content = "Hello from the agent"
    runner.run = AsyncMock(return_value={"messages": [msg]})
    return runner


def _list_tool_names(server: McpServer) -> list[str]:
    """List MCP tool names registered on the server."""
    tools = asyncio.get_event_loop().run_until_complete(server.mcp.list_tools())
    return [t.name for t in tools]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMcpServerInit:
    """Verify McpServer registers the expected MCP tools."""

    def test_creates_mcp_instance(self) -> None:
        runner = _make_runner_mock()
        registry = ToolRegistry()
        server = McpServer(runner=runner, registry=registry, name="test-server")

        assert server.mcp is not None
        assert server.mcp.name == "test-server"

    def test_chat_tool_registered(self) -> None:
        runner = _make_runner_mock()
        registry = ToolRegistry()
        server = McpServer(runner=runner, registry=registry)

        assert "chat" in _list_tool_names(server)

    def test_registry_tools_registered(self) -> None:
        runner = _make_runner_mock()
        registry = ToolRegistry()
        registry.register(_make_dummy_tool("search", "Search things"))
        registry.register(_make_dummy_tool("lookup", "Look up stuff"))

        server = McpServer(runner=runner, registry=registry)
        names = _list_tool_names(server)

        assert "search" in names
        assert "lookup" in names
        assert "chat" in names

    def test_empty_registry_only_chat(self) -> None:
        runner = _make_runner_mock()
        registry = ToolRegistry()
        server = McpServer(runner=runner, registry=registry)

        assert _list_tool_names(server) == ["chat"]


class TestMcpServerChatTool:
    """Verify the chat tool delegates to the AgentRunner."""

    @pytest.mark.asyncio
    async def test_chat_tool_calls_runner(self) -> None:
        runner = _make_runner_mock()
        registry = ToolRegistry()
        server = McpServer(runner=runner, registry=registry)

        result = await server.mcp.call_tool("chat", {"message": "hi", "thread_id": "t1"})
        runner.run.assert_awaited_once_with(message="hi", thread_id="t1")
        # call_tool returns a list of content items
        assert any("Hello from the agent" in str(item) for item in result)
