"""CLI entrypoint for the MCP server adapter."""

from __future__ import annotations

from rich.console import Console

from mr_lang.adapters.mcp import McpServer
from mr_lang.config import MrLangConfig
from mr_lang.core.graph import build_agent_graph
from mr_lang.core.registry import ToolRegistry
from mr_lang.core.runner import AgentRunner
from mr_lang.middleware.logging_mw import LoggingMiddleware
from mr_lang.providers.base import get_chat_model
from mr_lang.tools.builtin import list_files, read_file, run_shell, write_file
from mr_lang.workspace.builder import build_system_prompt
from mr_lang.workspace.loader import load_workspace

console = Console(stderr=True)


async def run_serve(
    workspace: str | None = None,
    provider: str = "ollama",
    model: str = "llama3",
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Wire up workspace/provider/graph/runner and start the MCP server."""
    config = MrLangConfig()

    # Load workspace if provided
    system_prompt = "You are a helpful assistant."
    if workspace:
        ws = load_workspace(workspace)
        system_prompt = build_system_prompt(ws)
        console.print(f"[green]Loaded workspace:[/green] {workspace}")

    # Set up model
    provider = provider or config.default_provider
    model = model or config.default_model
    chat_model = get_chat_model(provider, model)
    console.print(f"[green]Model:[/green] {provider}/{model}")

    # Set up tools
    registry = ToolRegistry()
    builtin_tools = [read_file, write_file, list_files, run_shell]
    for t in builtin_tools:
        registry.register(t)

    # Build graph with middleware
    middleware = [LoggingMiddleware()]
    graph = build_agent_graph(
        model=chat_model,
        tools=registry.list(),
        system_prompt=system_prompt,
        middleware=middleware,
    )
    runner = AgentRunner(graph)

    # Resolve host/port
    host = host or config.host
    port = port or config.port

    console.print(f"[green]Starting MCP server on[/green] {host}:{port}")
    server = McpServer(runner=runner, registry=registry)
    server.run(host=host, port=port)
