"""Memo — personal productivity assistant plugin for mr-lang."""

from __future__ import annotations

from pathlib import Path

from mr_lang.plugins.schema import PluginManifest


def get_plugin_manifest() -> PluginManifest:
    return PluginManifest.from_toml(Path(__file__).parent.parent.parent / "mr_lang_plugin.toml")
