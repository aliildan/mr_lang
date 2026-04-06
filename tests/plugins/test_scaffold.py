"""Tests for plugin project scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest

from mr_lang.exceptions import PluginError
from mr_lang.plugins.scaffold import WizardConfig, TelegramWizardConfig, scaffold_project


class TestScaffoldProject:
    def test_creates_basic_structure(self, tmp_path: Path) -> None:
        root = scaffold_project("my-plugin", path=tmp_path)

        assert root == tmp_path / "my-plugin"
        assert (root / "mr_lang_plugin.toml").is_file()
        assert (root / "pyproject.toml").is_file()
        assert (root / ".gitignore").is_file()
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

    # -- Memory --------------------------------------------------------

    def test_memory_enabled_adds_tools_doc_and_manifest(self, tmp_path: Path) -> None:
        wiz = WizardConfig(enable_memory=True)
        root = scaffold_project("mem-agent", path=tmp_path, wizard=wiz)

        from mr_lang.plugins.loader import PluginLoader

        m = PluginLoader.load_from_manifest(root / "mr_lang_plugin.toml")
        assert m.memory is not None
        assert m.memory.enabled is True

        tools_doc = (root / "workspace" / "TOOLS.md").read_text()
        assert "remember_fact" in tools_doc
        assert "recall_facts" in tools_doc
        assert "forget_fact" in tools_doc

    def test_no_memory_has_no_memory_tools(self, tmp_path: Path) -> None:
        root = scaffold_project("bare", path=tmp_path)

        from mr_lang.plugins.loader import PluginLoader

        m = PluginLoader.load_from_manifest(root / "mr_lang_plugin.toml")
        assert m.memory is None

        tools_doc = (root / "workspace" / "TOOLS.md").read_text()
        assert "remember_fact" not in tools_doc

    # -- RAG -----------------------------------------------------------

    def test_rag_enabled_adds_knowledge_tools_and_skill(self, tmp_path: Path) -> None:
        wiz = WizardConfig(enable_rag=True, rag_backend="chroma")
        root = scaffold_project("rag-agent", path=tmp_path, wizard=wiz)

        from mr_lang.plugins.loader import PluginLoader

        m = PluginLoader.load_from_manifest(root / "mr_lang_plugin.toml")
        assert m.rag is not None
        assert m.rag.backend == "chroma"

        tools_doc = (root / "workspace" / "TOOLS.md").read_text()
        assert "search_knowledge" in tools_doc
        assert "add_to_knowledge" in tools_doc

        # RAG gets research skill instead of example
        assert (root / "src" / "rag_agent" / "skills" / "research.SKILL.md").is_file()
        assert not (root / "src" / "rag_agent" / "skills" / "example.SKILL.md").exists()

    # -- Telegram ------------------------------------------------------

    def test_telegram_adds_config_and_deps(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TG_BOT_TELEGRAM_TOKEN", "test:token")
        tg = TelegramWizardConfig(
            bot_token="test:token",
            auth_mode="invite",
            admin_user_ids=[123],
        )
        wiz = WizardConfig(enable_telegram=True, telegram=tg)
        root = scaffold_project("tg-bot", path=tmp_path, wizard=wiz)

        from mr_lang.plugins.loader import PluginLoader

        m = PluginLoader.load_from_manifest(root / "mr_lang_plugin.toml")
        assert "python-telegram-bot>=21" in m.dependencies
        assert m.telegram is not None
        assert m.telegram.auth_mode == "invite"
        assert 123 in m.telegram.admin_user_ids

        # Token written to .env
        env = (root / ".env").read_text()
        assert "TG_BOT_TELEGRAM_TOKEN=test:token" in env

        # .env.example has placeholder
        env_example = (root / ".env.example").read_text()
        assert "TG_BOT_TELEGRAM_TOKEN=" in env_example

    def test_telegram_without_token_has_env_without_token(self, tmp_path: Path) -> None:
        """Telegram enabled but no token → .env has provider but no token line."""
        tg = TelegramWizardConfig(auth_mode="open")
        wiz = WizardConfig(enable_telegram=True, telegram=tg)
        root = scaffold_project("tg-empty", path=tmp_path, wizard=wiz)

        # .env has provider config but no telegram token
        env = (root / ".env").read_text()
        assert "MR_LANG_DEFAULT_PROVIDER=ollama" in env
        assert "TG_EMPTY_TELEGRAM_TOKEN" not in env

        env_example = (root / ".env.example").read_text()
        assert "TG_EMPTY_TELEGRAM_TOKEN=" in env_example

    # -- Wizard config overrides workspace content ---------------------

    def test_wizard_config_customizes_workspace(self, tmp_path: Path) -> None:
        wiz = WizardConfig(
            agent_name="Dr. Brain",
            agent_role="Science Tutor",
            language="German",
            personality="Enthusiastic and patient.",
            provider="anthropic",
            model="claude-sonnet-4-6",
            author="Ali",
            mcp_servers=["http://localhost:9000/sse"],
        )
        root = scaffold_project(
            "brain-bot", path=tmp_path, description="Test", wizard=wiz
        )

        identity = (root / "workspace" / "IDENTITY.md").read_text()
        assert "Dr. Brain" in identity
        assert "Science Tutor" in identity
        assert "German" in identity

        soul = (root / "workspace" / "SOUL.md").read_text()
        assert "Enthusiastic and patient" in soul

        agents = (root / "workspace" / "AGENTS.md").read_text()
        assert "anthropic" in agents
        assert "claude-sonnet-4-6" in agents

        manifest = (root / "mr_lang_plugin.toml").read_text()
        assert "Ali" in manifest
        assert "http://localhost:9000/sse" in manifest

    def test_memory_and_rag_together(self, tmp_path: Path) -> None:
        wiz = WizardConfig(
            enable_memory=True,
            enable_rag=True,
            rag_backend="chroma",
            embedding_model="nomic-embed-text",
        )
        root = scaffold_project("mem-rag", path=tmp_path, wizard=wiz)
        manifest = (root / "mr_lang_plugin.toml").read_text()
        assert "[plugin.memory]" in manifest
        assert "[plugin.rag]" in manifest
        assert 'backend = "chroma"' in manifest
        assert 'embedding_model = "nomic-embed-text"' in manifest

        from mr_lang.plugins.loader import PluginLoader

        m = PluginLoader.load_from_manifest(root / "mr_lang_plugin.toml")
        assert m.memory is not None
        assert m.rag is not None
        assert m.rag.backend == "chroma"

    def test_wizard_defaults_produce_valid_project(self, tmp_path: Path) -> None:
        """A completely default WizardConfig should scaffold without errors."""
        wiz = WizardConfig()
        root = scaffold_project("default-wiz", path=tmp_path, wizard=wiz)

        from mr_lang.plugins.loader import PluginLoader

        m = PluginLoader.load_from_manifest(root / "mr_lang_plugin.toml")
        assert m.name == "default-wiz"
        assert (root / "workspace" / "IDENTITY.md").is_file()
        assert (root / ".env.example").is_file()

    # -- Content varies with features ----------------------------------

    def test_features_produce_richer_content(self, tmp_path: Path) -> None:
        """Enabling features should produce more detailed workspace files."""
        bare = scaffold_project("bare-proj", path=tmp_path)
        wiz = WizardConfig(enable_memory=True, enable_rag=True, enable_telegram=True,
                           telegram=TelegramWizardConfig())
        rich = scaffold_project("rich-proj", path=tmp_path, wizard=wiz)

        bare_soul = (bare / "workspace" / "SOUL.md").read_text()
        rich_soul = (rich / "workspace" / "SOUL.md").read_text()
        assert len(rich_soul) > len(bare_soul)
        assert "Communication Style" in rich_soul

        bare_tools = (bare / "workspace" / "TOOLS.md").read_text()
        rich_tools = (rich / "workspace" / "TOOLS.md").read_text()
        assert "remember_fact" not in bare_tools
        assert "remember_fact" in rich_tools
        assert "search_knowledge" in rich_tools

    def test_gitignore_created(self, tmp_path: Path) -> None:
        root = scaffold_project("gi-test", path=tmp_path)
        gitignore = (root / ".gitignore").read_text()
        assert ".env" in gitignore
        assert "__pycache__" in gitignore
