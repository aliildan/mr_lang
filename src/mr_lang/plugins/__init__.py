"""Plugin/extension system for mr_lang."""

from __future__ import annotations

from mr_lang.plugins.integrations import load_plugins_into_registries
from mr_lang.plugins.loader import PluginLoader
from mr_lang.plugins.scaffold import TelegramWizardConfig, WizardConfig, scaffold_project
from mr_lang.plugins.schema import PluginManifest

__all__ = [
    "PluginLoader",
    "PluginManifest",
    "TelegramWizardConfig",
    "WizardConfig",
    "load_plugins_into_registries",
    "scaffold_project",
]
