"""Plugin discovery and activation."""

from __future__ import annotations

import logging
import os
import tomllib
from importlib.metadata import entry_points
from pathlib import Path

from mr_lang.core.registry import SkillRegistry, ToolRegistry
from mr_lang.exceptions import PluginError
from mr_lang.plugins.schema import PluginManifest

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "mr_lang_plugin.toml"


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

        manifest = PluginManifest(**{k: v for k, v in data.items() if v is not None})
        manifest.base_path = path.parent
        return manifest

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    @classmethod
    def discover_plugins(cls) -> list[PluginManifest]:
        """Find plugins from entry points, cwd, and ``MR_LANG_PLUGINS`` env var.

        Discovery sources (in order):
        1. ``mr_lang.plugins`` entry-point group (pip-installed plugins).
        2. ``mr_lang_plugin.toml`` in the current working directory.
        3. Colon-separated paths in the ``MR_LANG_PLUGINS`` environment variable.

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

        # 3. env var
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

        # Tools
        if manifest.tools_module:
            try:
                discover_tools_from_module(tool_registry, manifest.tools_module)
                logger.info(
                    "Loaded tools from %s for plugin %s",
                    manifest.tools_module,
                    manifest.name,
                )
            except Exception as exc:
                raise PluginError(
                    f"Failed to load tools for plugin '{manifest.name}': {exc}"
                ) from exc

        # Skills
        skills_path = manifest.resolve_skills()
        if skills_path and skills_path.is_dir():
            for skill in load_skills_dir(skills_path):
                skill_registry.register(skill)
            logger.info(
                "Loaded skills from %s for plugin %s",
                skills_path,
                manifest.name,
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
