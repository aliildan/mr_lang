"""MCP server adapter — exposes agent and tools via FastMCP."""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import Tool

from mr_lang.core.registry import ToolRegistry
from mr_lang.core.runner import AgentRunner
from mr_lang.exceptions import AdapterError


class McpServer:
    """Wraps an AgentRunner and ToolRegistry as an MCP server."""

    def __init__(
        self,
        runner: AgentRunner,
        registry: ToolRegistry,
        name: str = "mr-lang",
    ) -> None:
        self.runner = runner
        self.registry = registry
        self.mcp = FastMCP(name)
        self._register_chat_tool()
        self._register_registry_tools()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register_chat_tool(self) -> None:
        """Register a 'chat' tool that sends a message to the agent."""
        runner = self.runner

        async def chat(message: str, thread_id: str = "default") -> str:
            """Send a message to the mr-lang agent and return its response."""
            try:
                result = await runner.run(message=message, thread_id=thread_id)
                messages = result.get("messages", [])
                if messages:
                    last = messages[-1]
                    return last.content if hasattr(last, "content") else str(last)
                return ""
            except Exception as exc:
                raise AdapterError(f"Chat tool error: {exc}") from exc

        tool = Tool.from_function(
            chat,
            name="chat",
            description="Send a message to the agent.",
        )
        self.mcp.add_tool(tool)

    def _register_registry_tools(self) -> None:
        """Register each tool from the ToolRegistry as an MCP tool."""
        for tool in self.registry.list():
            self._wrap_langchain_tool(tool)

    def _wrap_langchain_tool(self, tool: Any) -> None:
        """Convert a LangChain BaseTool into an MCP tool registration."""
        lc_tool = tool

        async def _invoke(**kwargs: Any) -> str:
            result = await asyncio.to_thread(lc_tool.invoke, kwargs)
            if isinstance(result, str):
                return result
            return json.dumps(result, default=str)

        # Build a proper signature so FastMCP can inspect parameters.
        func = _make_async_fn(
            name=lc_tool.name,
            params=_extract_params(lc_tool),
            impl=_invoke,
            docstring=lc_tool.description or "",
        )

        mcp_tool = Tool.from_function(
            func,
            name=lc_tool.name,
            description=lc_tool.description or "",
        )
        self.mcp.add_tool(mcp_tool)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        """Start the MCP server (blocking)."""
        self.mcp.run(transport="sse", host=host, port=port)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _extract_params(lc_tool: Any) -> dict[str, tuple[type, Any]]:
    """Extract parameter names, types, and defaults from a LangChain tool."""
    params: dict[str, Any] = {}
    if lc_tool.args_schema:
        for field_name, field_info in lc_tool.args_schema.model_fields.items():
            params[field_name] = (field_info.annotation, field_info.default)
    return params


def _make_async_fn(
    name: str,
    params: dict[str, tuple[type, Any]],
    impl: Any,
    docstring: str,
) -> Any:
    """Dynamically create an async function with typed parameters.

    This is needed because FastMCP inspects the callable's signature to
    derive the tool's input schema.
    """
    sig_params = []
    annotations: dict[str, Any] = {}
    for pname, (ptype, pdefault) in params.items():
        annotations[pname] = ptype
        if pdefault is not None and not isinstance(pdefault, type):
            p = inspect.Parameter(
                pname,
                inspect.Parameter.KEYWORD_ONLY,
                default=pdefault,
                annotation=ptype,
            )
        else:
            p = inspect.Parameter(
                pname,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=ptype,
            )
        sig_params.append(p)

    async def wrapper(**kwargs: Any) -> str:
        return await impl(**kwargs)

    wrapper.__name__ = name
    wrapper.__qualname__ = name
    wrapper.__doc__ = docstring
    wrapper.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        parameters=sig_params, return_annotation=str
    )
    wrapper.__annotations__ = {**annotations, "return": str}
    return wrapper
