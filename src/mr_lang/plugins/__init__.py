"""Plugin/extension system for mr_lang."""

from __future__ import annotations

from mr_lang.plugins.loader import PluginLoader
from mr_lang.plugins.scaffold import scaffold_project
from mr_lang.plugins.schema import PluginManifest

__all__ = ["PluginLoader", "PluginManifest", "scaffold_project"]
