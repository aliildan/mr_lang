"""MCP server/client adapter."""

from __future__ import annotations

from mr_lang.adapters.mcp.client import load_mcp_tools
from mr_lang.adapters.mcp.server import McpServer

__all__ = ["McpServer", "load_mcp_tools"]
