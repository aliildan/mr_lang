"""Plugin integration helpers — load plugin tools, skills, and MCP servers."""

from __future__ import annotations

import logging

from mr_lang.core.registry import SkillRegistry, ToolRegistry
from mr_lang.plugins.loader import PluginLoader
from mr_lang.plugins.schema import PluginManifest

logger = logging.getLogger(__name__)


async def load_plugins_into_registries(
    tool_registry: ToolRegistry,
    skill_registry: SkillRegistry,
) -> None:
    """Discover and activate all plugins, including their external MCP tools.

    This is the main entry point for wiring plugins into any command (chat, serve,
    telegram). It handles:
    1. Plugin discovery (entry points, cwd manifest, MR_LANG_PLUGINS env var)
    2. Plugin activation (tools + skills)
    3. External MCP tool loading (declared in plugin manifests)

    Errors are logged as warnings — a broken plugin won't crash the system.
    """
    manifests = PluginLoader.discover_plugins()

    for manifest in manifests:
        logger.info("Activating plugin: %s v%s", manifest.name, manifest.version)
        PluginLoader.activate_plugin(manifest, tool_registry, skill_registry)

        # Load external MCP tools declared by the plugin
        if manifest.mcp_servers:
            await _load_mcp_tools_for_plugin(manifest, tool_registry)


async def _load_mcp_tools_for_plugin(
    manifest: PluginManifest,
    tool_registry: ToolRegistry,
) -> None:
    """Load MCP tools from all servers declared in a plugin manifest."""
    try:
        from mr_lang.adapters.mcp.client import load_mcp_tools
    except ImportError:
        logger.warning(
            "Plugin '%s' declares MCP servers but fastmcp is not installed. "
            "Install with: pip install mr-lang[mcp]",
            manifest.name,
        )
        return

    for server_url in manifest.mcp_servers:
        tools = await load_mcp_tools(server_url)
        for tool in tools:
            try:
                tool_registry.register(tool)
            except Exception as exc:
                logger.warning(
                    "Plugin '%s': skipping MCP tool '%s' from %s: %s",
                    manifest.name,
                    tool.name,
                    server_url,
                    exc,
                )
