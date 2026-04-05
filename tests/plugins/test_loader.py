"""Tests for plugin manifest loading and discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from mr_lang.exceptions import PluginError
from mr_lang.plugins.loader import PluginLoader
from mr_lang.plugins.schema import PluginManifest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_manifest_toml() -> str:
    return """\
[plugin]
name = "test-plugin"
version = "0.2.0"
description = "A test plugin"
author = "Tester"

[plugin.paths]
workspace = "./workspace"
skills = "./src/test_plugin/skills"
tools_module = "test_plugin.tools"

[plugin.mcp]
servers = ["http://localhost:9000"]

[plugin.cli]
module = "test_plugin.cli"

[plugin.dependencies]
packages = ["requests>=2"]
"""


@pytest.fixture
def manifest_file(tmp_path: Path, sample_manifest_toml: str) -> Path:
    p = tmp_path / "mr_lang_plugin.toml"
    p.write_text(sample_manifest_toml, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_from_manifest
# ---------------------------------------------------------------------------


class TestLoadFromManifest:
    def test_loads_valid_manifest(self, manifest_file: Path) -> None:
        m = PluginLoader.load_from_manifest(manifest_file)

        assert m.name == "test-plugin"
        assert m.version == "0.2.0"
        assert m.description == "A test plugin"
        assert m.author == "Tester"
        assert m.workspace_dir == Path("./workspace")
        assert m.skills_dir == Path("./src/test_plugin/skills")
        assert m.tools_module == "test_plugin.tools"
        assert m.mcp_servers == ["http://localhost:9000"]
        assert m.cli_module == "test_plugin.cli"
        assert m.dependencies == ["requests>=2"]

    def test_sets_base_path(self, manifest_file: Path) -> None:
        m = PluginLoader.load_from_manifest(manifest_file)
        assert m.base_path == manifest_file.parent

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(PluginError, match="Manifest not found"):
            PluginLoader.load_from_manifest(tmp_path / "nonexistent.toml")

    def test_missing_plugin_section_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "mr_lang_plugin.toml"
        p.write_text("[other]\nfoo = 1\n", encoding="utf-8")
        with pytest.raises(PluginError, match="Missing \\[plugin\\] section"):
            PluginLoader.load_from_manifest(p)

    def test_minimal_manifest(self, tmp_path: Path) -> None:
        p = tmp_path / "mr_lang_plugin.toml"
        p.write_text('[plugin]\nname = "minimal"\n', encoding="utf-8")
        m = PluginLoader.load_from_manifest(p)
        assert m.name == "minimal"
        assert m.version == "0.1.0"
        assert m.tools_module is None
        assert m.dependencies == []


# ---------------------------------------------------------------------------
# resolve paths
# ---------------------------------------------------------------------------


class TestResolvePaths:
    def test_resolve_workspace(self, manifest_file: Path) -> None:
        m = PluginLoader.load_from_manifest(manifest_file)
        ws = m.resolve_workspace()
        assert ws is not None
        assert ws == (manifest_file.parent / "workspace").resolve()

    def test_resolve_skills(self, manifest_file: Path) -> None:
        m = PluginLoader.load_from_manifest(manifest_file)
        sd = m.resolve_skills()
        assert sd is not None
        assert sd == (manifest_file.parent / "src/test_plugin/skills").resolve()

    def test_resolve_none_when_no_path(self, tmp_path: Path) -> None:
        p = tmp_path / "mr_lang_plugin.toml"
        p.write_text('[plugin]\nname = "bare"\n', encoding="utf-8")
        m = PluginLoader.load_from_manifest(p)
        assert m.resolve_workspace() is None
        assert m.resolve_skills() is None


# ---------------------------------------------------------------------------
# discover_plugins
# ---------------------------------------------------------------------------


class TestDiscoverPlugins:
    def test_discovers_from_cwd(
        self, tmp_path: Path, sample_manifest_toml: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "mr_lang_plugin.toml").write_text(
            sample_manifest_toml, encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        plugins = PluginLoader.discover_plugins()
        names = [p.name for p in plugins]
        assert "test-plugin" in names

    def test_discovers_from_env_var(
        self, tmp_path: Path, sample_manifest_toml: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "mr_lang_plugin.toml").write_text(
            sample_manifest_toml, encoding="utf-8"
        )
        # chdir somewhere else so cwd doesn't match
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("MR_LANG_PLUGINS", str(plugin_dir))

        plugins = PluginLoader.discover_plugins()
        names = [p.name for p in plugins]
        assert "test-plugin" in names

    def test_deduplicates(
        self, tmp_path: Path, sample_manifest_toml: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same manifest found via cwd and env should appear only once."""
        (tmp_path / "mr_lang_plugin.toml").write_text(
            sample_manifest_toml, encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("MR_LANG_PLUGINS", str(tmp_path))

        plugins = PluginLoader.discover_plugins()
        assert sum(1 for p in plugins if p.name == "test-plugin") == 1

    def test_empty_discovery(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("MR_LANG_PLUGINS", raising=False)
        # May still find entry-point plugins, so just verify it doesn't crash.
        PluginLoader.discover_plugins()


# ---------------------------------------------------------------------------
# activate_plugin (tools + skills)
# ---------------------------------------------------------------------------


class TestActivatePlugin:
    def test_activate_with_skills(self, tmp_path: Path) -> None:
        """Activation loads SKILL.md files from skills_dir."""
        from mr_lang.core.registry import SkillRegistry, ToolRegistry

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "greet.SKILL.md").write_text(
            "---\nname: greet\ndescription: Greet the user\nemoji: '👋'\n"
            "requires:\n  tools: []\n  env: []\ntags: [demo]\n---\n\nSay hello.\n",
            encoding="utf-8",
        )

        manifest = PluginManifest(name="sk-test", skills_dir="./skills")
        manifest.base_path = tmp_path

        tool_reg = ToolRegistry()
        skill_reg = SkillRegistry()
        PluginLoader.activate_plugin(manifest, tool_reg, skill_reg)

        assert len(skill_reg) == 1
        assert skill_reg.names() == ["greet"]

    def test_activate_no_modules_is_noop(self) -> None:
        """Activating a plugin with nothing configured should not crash."""
        from mr_lang.core.registry import SkillRegistry, ToolRegistry

        manifest = PluginManifest(name="empty")
        tool_reg = ToolRegistry()
        skill_reg = SkillRegistry()
        PluginLoader.activate_plugin(manifest, tool_reg, skill_reg)

        assert len(tool_reg) == 0
        assert len(skill_reg) == 0
