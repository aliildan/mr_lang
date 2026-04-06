"""CLI entrypoint for the MCP server adapter."""

from __future__ import annotations

from rich.console import Console

from mr_lang.adapters.mcp import McpServer
from mr_lang.cli.setup import setup_agent

console = Console(stderr=True)


async def run_serve(
    workspace: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    host: str | None = None,
    port: int | None = None,
    plugin: str | None = None,
) -> None:
    """Wire up workspace/provider/graph/runner and start the MCP server."""
    components = await setup_agent(
        workspace=workspace,
        provider=provider,
        model=model,
        plugin_name=plugin,
    )

    # Resolve host/port from config
    host = host or components.config.host
    port = port or components.config.port

    console.print(f"[green]Starting MCP server on[/green] {host}:{port}")
    server = McpServer(runner=components.runner, registry=components.registry)
    server.run(host=host, port=port)
