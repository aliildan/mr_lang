"""MCP client adapter — connects to an external MCP server and wraps tools as LangChain tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Client
from langchain_core.tools import BaseTool, StructuredTool


async def load_mcp_tools(server_url: str) -> list[BaseTool]:
    """Connect to an MCP server and return each remote tool as a LangChain BaseTool.

    Args:
        server_url: URL of the MCP server (e.g. ``http://127.0.0.1:8000/sse``).

    Returns:
        A list of :class:`StructuredTool` instances that proxy calls to the remote
        MCP server.
    """
    tools: list[BaseTool] = []

    async with Client(server_url) as client:
        remote_tools = await client.list_tools()

        for rt in remote_tools:
            tool = _make_langchain_tool(rt, server_url)
            tools.append(tool)

    return tools


def _make_langchain_tool(remote_tool: Any, server_url: str) -> StructuredTool:
    """Create a LangChain StructuredTool that proxies to an MCP remote tool."""
    tool_name = remote_tool.name
    tool_description = remote_tool.description or ""

    async def _call_remote(**kwargs: Any) -> str:
        async with Client(server_url) as client:
            result = await client.call_tool(tool_name, arguments=kwargs)
            # FastMCP client returns a list of content items; concatenate text parts.
            if isinstance(result, list):
                parts = []
                for item in result:
                    if hasattr(item, "text"):
                        parts.append(item.text)
                    else:
                        parts.append(str(item))
                return "\n".join(parts)
            return str(result)

    return StructuredTool.from_function(
        coroutine=_call_remote,
        name=tool_name,
        description=tool_description,
    )
