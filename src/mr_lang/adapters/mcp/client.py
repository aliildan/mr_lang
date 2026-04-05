"""MCP client adapter — connects to external MCP servers and wraps tools as LangChain tools."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

logger = logging.getLogger(__name__)


async def load_mcp_tools(server_url: str) -> list[BaseTool]:
    """Connect to an MCP server and return each remote tool as a LangChain BaseTool.

    Each tool creates its own connection per call. This is robust against server
    restarts and avoids holding long-lived connections.

    Args:
        server_url: URL of the MCP server (e.g. ``http://127.0.0.1:8000/sse``).

    Returns:
        A list of :class:`StructuredTool` instances that proxy calls to the remote
        MCP server. Returns an empty list if the server is unreachable.
    """
    try:
        from fastmcp import Client
    except ImportError as err:
        raise ImportError("Install fastmcp: pip install mr-lang[mcp]") from err

    tools: list[BaseTool] = []

    try:
        async with Client(server_url) as client:
            remote_tools = await client.list_tools()

        for rt in remote_tools:
            tool = _make_langchain_tool(rt, server_url)
            tools.append(tool)

        logger.info("Loaded %d MCP tool(s) from %s", len(tools), server_url)

    except Exception as exc:
        logger.warning(
            "Could not connect to MCP server at %s: %s — "
            "tools will not be available. Start the server and retry.",
            server_url,
            exc,
        )

    return tools


def _make_langchain_tool(remote_tool: Any, server_url: str) -> StructuredTool:
    """Create a LangChain StructuredTool that proxies to an MCP remote tool.

    Each invocation opens a fresh connection to the MCP server. This avoids
    stale connection issues and works across server restarts.
    """
    from fastmcp import Client

    tool_name = remote_tool.name
    tool_description = remote_tool.description or f"Remote MCP tool: {tool_name}"

    async def _call_remote(**kwargs: Any) -> str:
        try:
            async with Client(server_url) as client:
                result = await client.call_tool(tool_name, arguments=kwargs)
                if isinstance(result, list):
                    parts = []
                    for item in result:
                        if hasattr(item, "text"):
                            parts.append(item.text)
                        else:
                            parts.append(str(item))
                    return "\n".join(parts)
                return str(result)
        except Exception as exc:
            return f"Error calling MCP tool '{tool_name}': {exc}"

    return StructuredTool.from_function(
        coroutine=_call_remote,
        name=tool_name,
        description=tool_description,
    )
