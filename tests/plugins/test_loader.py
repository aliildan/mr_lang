"""Tests for plugin manifest loading and discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from mr_lang.exceptions import PluginError
from mr_lang.plugins.loader import PluginLoader, _expand_env_vars
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

    def test_discovers_from_plugins_dir(
        self, tmp_path: Path, sample_manifest_toml: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Plugins in ./plugins/<name>/ are auto-discovered."""
        plugins_dir = tmp_path / "plugins" / "my-agent"
        plugins_dir.mkdir(parents=True)
        (plugins_dir / "mr_lang_plugin.toml").write_text(
            sample_manifest_toml, encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("MR_LANG_PLUGINS", raising=False)

        plugins = PluginLoader.discover_plugins()
        names = [p.name for p in plugins]
        assert "test-plugin" in names

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


# ---------------------------------------------------------------------------
# _expand_env_vars
# ---------------------------------------------------------------------------


class TestExpandEnvVars:
    def test_expands_single_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TOKEN", "secret123")
        assert _expand_env_vars("${MY_TOKEN}") == "secret123"

    def test_expands_multiple_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "8080")
        assert _expand_env_vars("${HOST}:${PORT}") == "localhost:8080"

    def test_passthrough_no_vars(self) -> None:
        assert _expand_env_vars("plain_string") == "plain_string"

    def test_missing_var_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        with pytest.raises(PluginError, match="NONEXISTENT_VAR.*not set"):
            _expand_env_vars("${NONEXISTENT_VAR}")


# ---------------------------------------------------------------------------
# Telegram config in manifest
# ---------------------------------------------------------------------------


class TestTelegramConfig:
    def test_manifest_without_telegram(self, manifest_file: Path) -> None:
        m = PluginLoader.load_from_manifest(manifest_file)
        assert m.telegram is None

    def test_manifest_with_telegram(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_BOT_TOKEN", "123:ABC")
        toml = """\
[plugin]
name = "tg-test"

[plugin.telegram]
bot_token = "${TEST_BOT_TOKEN}"
auth_mode = "invite"
admin_user_ids = [111]
allowed_user_ids = [111, 222]
invite_codes = ["code1"]
max_uses_per_code = 5
"""
        p = tmp_path / "mr_lang_plugin.toml"
        p.write_text(toml, encoding="utf-8")

        m = PluginLoader.load_from_manifest(p)
        assert m.telegram is not None
        assert m.telegram.bot_token == "123:ABC"
        assert m.telegram.auth_mode == "invite"
        assert m.telegram.admin_user_ids == [111]
        assert m.telegram.allowed_user_ids == [111, 222]
        assert m.telegram.invite_codes == ["code1"]
        assert m.telegram.max_uses_per_code == 5

    def test_telegram_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BOT_TOK", "tok:en")
        toml = """\
[plugin]
name = "tg-minimal"

[plugin.telegram]
bot_token = "${BOT_TOK}"
"""
        p = tmp_path / "mr_lang_plugin.toml"
        p.write_text(toml, encoding="utf-8")

        m = PluginLoader.load_from_manifest(p)
        assert m.telegram is not None
        assert m.telegram.bot_token == "tok:en"
        assert m.telegram.auth_mode is None
        assert m.telegram.admin_user_ids == []
        assert m.telegram.max_uses_per_code is None

    def test_telegram_reads_plugin_local_env(self, tmp_path: Path) -> None:
        """Token resolved from .env next to mr_lang_plugin.toml."""
        (tmp_path / ".env").write_text(
            "MY_LOCAL_TOKEN=local:secret\n", encoding="utf-8"
        )
        toml = """\
[plugin]
name = "tg-local"

[plugin.telegram]
bot_token = "${MY_LOCAL_TOKEN}"
"""
        p = tmp_path / "mr_lang_plugin.toml"
        p.write_text(toml, encoding="utf-8")

        m = PluginLoader.load_from_manifest(p)
        assert m.telegram is not None
        assert m.telegram.bot_token == "local:secret"

    def test_telegram_missing_env_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("MISSING_TOKEN", raising=False)
        toml = """\
[plugin]
name = "tg-fail"

[plugin.telegram]
bot_token = "${MISSING_TOKEN}"
"""
        p = tmp_path / "mr_lang_plugin.toml"
        p.write_text(toml, encoding="utf-8")

        with pytest.raises(PluginError, match="MISSING_TOKEN.*not set"):
            PluginLoader.load_from_manifest(p)
