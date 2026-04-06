"""MCP client adapter — connects to external MCP servers and wraps tools as LangChain tools."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, create_model

if TYPE_CHECKING:
    from mr_lang.plugins.schema import McpServerConfig

logger = logging.getLogger(__name__)

_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _build_args_schema(input_schema: dict) -> type[BaseModel]:
    """Build a Pydantic model from an MCP tool's JSON inputSchema.

    This gives StructuredTool a concrete parameter schema so the LLM passes
    arguments by name (e.g. url='...') rather than as a wrapped kwargs dict.
    """
    properties: dict = input_schema.get("properties") or {}
    required: set[str] = set(input_schema.get("required") or [])
    fields: dict[str, Any] = {}
    for field_name, prop in properties.items():
        python_type = _JSON_TYPE_MAP.get(prop.get("type", "string"), str)
        description = prop.get("description", "")
        if field_name in required:
            fields[field_name] = (python_type, Field(..., description=description))
        else:
            fields[field_name] = (python_type | None, Field(None, description=description))
    if not fields:
        return create_model("Args")
    return create_model("Args", **fields)


async def load_mcp_tools(server: str | McpServerConfig) -> list[BaseTool]:
    """Connect to an MCP server and return each remote tool as a LangChain BaseTool.

    Supports two transport types:
    - **URL / SSE**: pass a URL string or a ``McpServerConfig`` with ``url`` set.
      Each tool call opens a fresh connection (robust against server restarts).
    - **stdio**: pass a ``McpServerConfig`` with ``command`` set.
      Uses ``fastmcp.client.transports.StdioTransport`` with ``keep_alive=True``
      so the subprocess persists across calls (required for stateful tools like
      browser automation).

    Args:
        server: URL string (legacy), or a :class:`~mr_lang.plugins.schema.McpServerConfig`.

    Returns:
        List of :class:`StructuredTool` instances that proxy calls to the MCP server.
        Returns an empty list if the server is unreachable.
    """
    # Resolve to (transport_or_url, server_name)
    if isinstance(server, str):
        return await _load_from_url(server, name=server)

    from mr_lang.plugins.schema import McpServerConfig

    assert isinstance(server, McpServerConfig)

    if server.url:
        return await _load_from_url(server.url, name=server.name)

    if server.command:
        return await _load_from_stdio(server)

    logger.warning("MCP server '%s' has neither url nor command — skipping.", server.name)
    return []


async def _load_from_url(url: str, name: str) -> list[BaseTool]:
    """Load tools from a URL-based (SSE) MCP server."""
    try:
        from fastmcp import Client
    except ImportError as err:
        raise ImportError("Install fastmcp: pip install mr-lang[mcp]") from err

    tools: list[BaseTool] = []
    try:
        async with Client(url) as client:
            remote_tools = await client.list_tools()
        for rt in remote_tools:
            tools.append(_make_url_tool(rt, url))
        logger.info("Loaded %d MCP tool(s) from %s", len(tools), url)
    except Exception as exc:
        logger.warning(
            "Could not connect to MCP server '%s' at %s: %s — "
            "tools will not be available. Start the server and retry.",
            name,
            url,
            exc,
        )
    return tools


async def _load_from_stdio(server: McpServerConfig) -> list[BaseTool]:
    """Load tools from a stdio (subprocess) MCP server.

    The StdioTransport is created with keep_alive=True so the subprocess stays
    alive between tool calls — critical for stateful servers (e.g. browser tools).
    """
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    env = server.env if server.env else None
    transport = StdioTransport(
        server.command,  # type: ignore[arg-type]
        server.args,
        env=env,
        cwd=server.cwd,
        keep_alive=True,
    )

    tools: list[BaseTool] = []
    try:
        async with Client(transport) as client:
            remote_tools = await client.list_tools()
        for rt in remote_tools:
            tools.append(_make_stdio_tool(rt, transport, server.name))
        logger.info(
            "Loaded %d MCP tool(s) from stdio server '%s' (%s %s)",
            len(tools),
            server.name,
            server.command,
            " ".join(server.args),
        )
    except Exception as exc:
        logger.warning(
            "Could not start stdio MCP server '%s' (%s %s): %s — tools will not be available.",
            server.name,
            server.command,
            " ".join(server.args),
            exc,
        )
    return tools


def _make_url_tool(remote_tool: Any, server_url: str) -> StructuredTool:
    """Create a LangChain tool that proxies to a URL-based MCP tool.

    Opens a fresh connection per call for robustness against server restarts.
    """
    from fastmcp import Client

    tool_name = remote_tool.name
    tool_description = remote_tool.description or f"Remote MCP tool: {tool_name}"
    input_schema = getattr(remote_tool, "inputSchema", None) or {}
    args_schema = _build_args_schema(input_schema)

    async def _call_remote(**kwargs: Any) -> str:
        try:
            async with Client(server_url) as client:
                result = await client.call_tool(
                    tool_name,
                    arguments={k: v for k, v in kwargs.items() if v is not None},
                )
                return _extract_text(result)
        except Exception as exc:
            return f"Error calling MCP tool '{tool_name}': {exc}"

    return StructuredTool.from_function(
        coroutine=_call_remote,
        name=tool_name,
        description=tool_description,
        args_schema=args_schema,
    )


def _make_stdio_tool(remote_tool: Any, transport: Any, server_name: str) -> StructuredTool:
    """Create a LangChain tool that proxies to a stdio MCP tool.

    Reuses the keep-alive transport so the subprocess is not restarted per call.
    """
    from fastmcp import Client

    tool_name = remote_tool.name
    tool_description = remote_tool.description or f"Remote MCP tool: {tool_name}"
    input_schema = getattr(remote_tool, "inputSchema", None) or {}
    args_schema = _build_args_schema(input_schema)

    async def _call_remote(**kwargs: Any) -> str:
        try:
            async with Client(transport) as client:
                result = await client.call_tool(
                    tool_name,
                    arguments={k: v for k, v in kwargs.items() if v is not None},
                )
                return _extract_text(result)
        except Exception as exc:
            return f"Error calling MCP tool '{tool_name}' on '{server_name}': {exc}"

    return StructuredTool.from_function(
        coroutine=_call_remote,
        name=tool_name,
        description=tool_description,
        args_schema=args_schema,
    )


# Tool results larger than this are likely binary blobs (e.g. base64 screenshots).
# Truncate to keep only the header text so we don't blow up the LLM context window.
_MAX_TOOL_RESULT_CHARS = 2000


def _extract_text(result: Any) -> str:
    """Flatten an MCP tool result into a plain string, truncating large binary blobs."""
    if isinstance(result, list):
        parts = []
        for item in result:
            if hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))
        text = "\n".join(parts)
    else:
        text = str(result)

    if len(text) > _MAX_TOOL_RESULT_CHARS:
        text = text[:_MAX_TOOL_RESULT_CHARS] + f"\n...[result truncated — {len(text)} chars total]"

    return text
