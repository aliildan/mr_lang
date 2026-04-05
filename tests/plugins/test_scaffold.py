"""Tests for plugin project scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest

from mr_lang.exceptions import PluginError
from mr_lang.plugins.scaffold import scaffold_project


class TestScaffoldProject:
    def test_creates_basic_structure(self, tmp_path: Path) -> None:
        root = scaffold_project("my-plugin", path=tmp_path, template="basic")

        assert root == tmp_path / "my-plugin"
        assert (root / "mr_lang_plugin.toml").is_file()
        assert (root / "pyproject.toml").is_file()
        assert (root / "src" / "my_plugin" / "__init__.py").is_file()
        assert (root / "src" / "my_plugin" / "tools" / "__init__.py").is_file()
        assert (root / "src" / "my_plugin" / "skills" / "example.SKILL.md").is_file()
        assert (root / "workspace" / "IDENTITY.md").is_file()
        assert (root / "workspace" / "SOUL.md").is_file()
        assert (root / "workspace" / "USER.md").is_file()
        assert (root / "workspace" / "TOOLS.md").is_file()
        assert (root / "workspace" / "AGENTS.md").is_file()
        assert (root / "tests" / "__init__.py").is_file()

    def test_manifest_is_valid_toml(self, tmp_path: Path) -> None:
        """The generated mr_lang_plugin.toml should be loadable."""
        from mr_lang.plugins.loader import PluginLoader

        root = scaffold_project("toml-test", path=tmp_path)
        m = PluginLoader.load_from_manifest(root / "mr_lang_plugin.toml")
        assert m.name == "toml-test"
        assert m.tools_module == "toml_test.tools"

    def test_telegram_template(self, tmp_path: Path) -> None:
        root = scaffold_project("tg-bot", path=tmp_path, template="telegram-bot")
        identity = (root / "workspace" / "IDENTITY.md").read_text()
        assert "Telegram" in identity

        from mr_lang.plugins.loader import PluginLoader

        m = PluginLoader.load_from_manifest(root / "mr_lang_plugin.toml")
        assert "python-telegram-bot>=21" in m.dependencies

    def test_teaching_template(self, tmp_path: Path) -> None:
        root = scaffold_project(
            "teach-assist", path=tmp_path, template="teaching-assistant"
        )
        identity = (root / "workspace" / "IDENTITY.md").read_text()
        assert "Teaching" in identity

    def test_unknown_template_raises(self, tmp_path: Path) -> None:
        with pytest.raises(PluginError, match="Unknown template"):
            scaffold_project("bad", path=tmp_path, template="nonexistent")

    def test_existing_dir_raises(self, tmp_path: Path) -> None:
        (tmp_path / "exists").mkdir()
        with pytest.raises(PluginError, match="already exists"):
            scaffold_project("exists", path=tmp_path)

    def test_description_in_manifest(self, tmp_path: Path) -> None:
        root = scaffold_project(
            "desc-test", path=tmp_path, description="Custom description"
        )
        content = (root / "mr_lang_plugin.toml").read_text()
        assert "Custom description" in content
