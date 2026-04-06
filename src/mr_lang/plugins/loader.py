"""Plugin discovery and activation."""

from __future__ import annotations

import logging
import os
import re
import tomllib
from importlib.metadata import entry_points
from pathlib import Path

from mr_lang.core.registry import SkillRegistry, ToolRegistry
from mr_lang.exceptions import PluginError
from mr_lang.plugins.schema import PluginManifest

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "mr_lang_plugin.toml"


def _expand_env_vars(value: str, plugin_dir: Path | None = None) -> str:
    """Replace ``${VAR_NAME}`` patterns with environment variable values.

    Resolution order:
    1. ``os.environ`` (shell exports, process env)
    2. Plugin's own ``.env`` file (next to ``mr_lang_plugin.toml``)
    3. Project-level ``.env`` in cwd
    """
    from dotenv import dotenv_values

    _plugin_env: dict[str, str | None] | None = None
    _project_env: dict[str, str | None] | None = None

    def _replacer(match: re.Match[str]) -> str:
        nonlocal _plugin_env, _project_env
        var_name = match.group(1)

        # 1. Shell / process environment
        result = os.environ.get(var_name)

        # 2. Plugin's own .env
        if result is None and plugin_dir is not None:
            if _plugin_env is None:
                _plugin_env = dotenv_values(plugin_dir / ".env")
            result = _plugin_env.get(var_name)

        # 3. Project-level .env (cwd)
        if result is None:
            if _project_env is None:
                _project_env = dotenv_values(".env")
            result = _project_env.get(var_name)

        if result is None:
            raise PluginError(f"Environment variable ${{{var_name}}} is not set")
        return result

    return re.sub(r"\$\{([^}]+)\}", _replacer, value)


class PluginLoader:
    """Discovers and activates mr_lang plugins."""

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @staticmethod
    def load_from_manifest(path: Path) -> PluginManifest:
        """Read a *mr_lang_plugin.toml* file and return a PluginManifest.

        Args:
            path: Path to the TOML manifest file.

        Returns:
            Parsed PluginManifest with base_path set.
        """
        path = Path(path).resolve()
        if not path.exists():
            raise PluginError(f"Manifest not found: {path}")

        with path.open("rb") as fh:
            raw = tomllib.load(fh)

        plugin_section = raw.get("plugin")
        if plugin_section is None:
            raise PluginError(f"Missing [plugin] section in {path}")

        # Flatten nested tables into PluginManifest fields.
        data: dict = {
            "name": plugin_section.get("name", ""),
            "version": plugin_section.get("version", "0.1.0"),
            "description": plugin_section.get("description", ""),
            "author": plugin_section.get("author", ""),
        }

        paths = plugin_section.get("paths", {})
        data["workspace_dir"] = paths.get("workspace")
        data["skills_dir"] = paths.get("skills")
        data["tools_module"] = paths.get("tools_module")

        mcp = plugin_section.get("mcp", {})
        data["mcp_servers"] = mcp.get("servers", [])

        cli = plugin_section.get("cli", {})
        data["cli_module"] = cli.get("module")

        deps = plugin_section.get("dependencies", {})
        data["dependencies"] = deps.get("packages", [])

        telegram = plugin_section.get("telegram")
        if telegram is not None:
            raw_token = telegram.get("bot_token", "")
            telegram["bot_token"] = _expand_env_vars(raw_token, plugin_dir=path.parent)
            data["telegram"] = telegram

        memory = plugin_section.get("memory")
        if memory is not None:
            data["memory"] = memory

        rag = plugin_section.get("rag")
        if rag is not None:
            data["rag"] = rag

        manifest = PluginManifest(**{k: v for k, v in data.items() if v is not None})
        manifest.base_path = path.parent
        return manifest

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    @classmethod
    def discover_plugins(cls) -> list[PluginManifest]:
        """Find plugins from entry points, cwd, plugins dir, and env var.

        Discovery sources (in order):
        1. ``mr_lang.plugins`` entry-point group (pip-installed plugins).
        2. ``mr_lang_plugin.toml`` in the current working directory.
        3. Each subdirectory of ``./plugins/`` in the current working directory.
        4. Colon-separated paths in the ``MR_LANG_PLUGINS`` environment variable.

        Returns:
            De-duplicated list of PluginManifest instances.
        """
        seen: set[str] = set()
        manifests: list[PluginManifest] = []

        def _add(m: PluginManifest) -> None:
            if m.name not in seen:
                seen.add(m.name)
                manifests.append(m)

        # 1. entry points
        for m in cls._from_entry_points():
            _add(m)

        # 2. cwd
        cwd_manifest = Path.cwd() / MANIFEST_FILENAME
        if cwd_manifest.exists():
            try:
                _add(cls.load_from_manifest(cwd_manifest))
            except PluginError as exc:
                logger.warning("Skipping cwd manifest: %s", exc)

        # 3. ./plugins/ subdirectories
        plugins_dir = Path.cwd() / "plugins"
        if plugins_dir.is_dir():
            for child in sorted(plugins_dir.iterdir()):
                if not child.is_dir():
                    continue
                child_manifest = child / MANIFEST_FILENAME
                if child_manifest.exists():
                    try:
                        _add(cls.load_from_manifest(child_manifest))
                    except PluginError as exc:
                        logger.warning("Skipping plugin %s: %s", child.name, exc)

        # 4. env var
        env_val = os.environ.get("MR_LANG_PLUGINS", "")
        for raw_path in env_val.split(":"):
            raw_path = raw_path.strip()
            if not raw_path:
                continue
            p = Path(raw_path)
            manifest_path = p / MANIFEST_FILENAME if p.is_dir() else p
            if manifest_path.exists():
                try:
                    _add(cls.load_from_manifest(manifest_path))
                except PluginError as exc:
                    logger.warning("Skipping env plugin %s: %s", raw_path, exc)

        return manifests

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    @staticmethod
    def activate_plugin(
        manifest: PluginManifest,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
    ) -> None:
        """Activate a plugin by loading its tools and skills into registries.

        Args:
            manifest: The plugin to activate.
            tool_registry: Registry to load tools into.
            skill_registry: Registry to load skills into.
        """
        from mr_lang.skills.loader import load_skills_dir
        from mr_lang.tools.discovery import discover_tools_from_module

        # Tools — warn instead of crash if module is empty or not installed yet
        if manifest.tools_module:
            try:
                discover_tools_from_module(tool_registry, manifest.tools_module)
                logger.info(
                    "Loaded tools from %s for plugin %s",
                    manifest.tools_module,
                    manifest.name,
                )
            except ImportError:
                logger.warning(
                    "Plugin '%s': tools_module '%s' not found — "
                    "install the plugin or add tools later.",
                    manifest.name,
                    manifest.tools_module,
                )
            except Exception as exc:
                logger.warning(
                    "Plugin '%s': failed to load tools from '%s': %s",
                    manifest.name,
                    manifest.tools_module,
                    exc,
                )

        # Skills — warn if skills directory is declared but missing
        skills_path = manifest.resolve_skills()
        if manifest.skills_dir and (not skills_path or not skills_path.is_dir()):
            logger.warning(
                "Plugin '%s': skills_dir '%s' not found — add skills later.",
                manifest.name,
                manifest.skills_dir,
            )
        elif skills_path and skills_path.is_dir():
            for skill in load_skills_dir(skills_path):
                skill_registry.register(skill)
            logger.info(
                "Loaded skills from %s for plugin %s",
                skills_path,
                manifest.name,
            )

        # Workspace — warn if workspace directory is declared but missing
        ws_path = manifest.resolve_workspace()
        if manifest.workspace_dir and (not ws_path or not ws_path.is_dir()):
            logger.warning(
                "Plugin '%s': workspace_dir '%s' not found — add workspace files later.",
                manifest.name,
                manifest.workspace_dir,
            )

        # MCP servers — warn if configured but not reachable (validated at runtime)
        if manifest.mcp_servers:
            logger.info(
                "Plugin '%s' declares %d MCP server(s) — will connect at runtime.",
                manifest.name,
                len(manifest.mcp_servers),
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _from_entry_points(cls) -> list[PluginManifest]:
        """Load manifests advertised via the ``mr_lang.plugins`` entry-point group."""
        group = "mr_lang.plugins"
        eps = entry_points(group=group)

        manifests: list[PluginManifest] = []
        for ep in eps:
            try:
                get_manifest = ep.load()
                m = get_manifest()
                if isinstance(m, PluginManifest):
                    manifests.append(m)
                else:
                    logger.warning(
                        "Entry point %s did not return a PluginManifest", ep.name
                    )
            except Exception as exc:
                logger.warning("Failed to load plugin entry point %s: %s", ep.name, exc)
        return manifests
