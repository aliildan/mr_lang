"""Shared setup logic for CLI commands (chat, serve, telegram)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from langgraph.store.base import BaseStore
from rich.console import Console

from mr_lang.config import MrLangConfig
from mr_lang.core.graph import build_agent_graph
from mr_lang.core.registry import SkillRegistry, ToolRegistry
from mr_lang.core.runner import AgentRunner
from mr_lang.exceptions import SkillError
from mr_lang.memory.checkpointer import get_checkpointer
from mr_lang.memory.store import get_store
from mr_lang.middleware.logging_mw import LoggingMiddleware
from mr_lang.observability.collector import EventCollector
from mr_lang.observability.middleware import ObservabilityMiddleware
from mr_lang.plugins.integrations import load_plugins_into_registries
from mr_lang.plugins.loader import PluginLoader
from mr_lang.plugins.schema import PluginManifest
from mr_lang.providers.base import get_chat_model
from mr_lang.skills.executor import skill_to_prompt_section, validate_skill_requirements
from mr_lang.tools.builtin import list_files, read_file, run_shell, write_file
from mr_lang.tools.builtin.filesystem import set_allowed_paths
from mr_lang.tools.builtin.shell import set_blocked_commands
from mr_lang.workspace.builder import build_system_prompt
from mr_lang.workspace.loader import load_workspace

if TYPE_CHECKING:
    from mr_lang.middleware.base import BaseMiddleware

console = Console(stderr=True)


def _load_plugin_env(plugin_name: str) -> None:
    """Load a plugin's .env into the process environment (without overriding existing vars).

    This allows the plugin's MR_LANG_DEFAULT_PROVIDER, MR_LANG_DEFAULT_MODEL, etc.
    to be picked up by pydantic-settings when MrLangConfig() is created.
    """
    import os

    from dotenv import dotenv_values

    manifests = PluginLoader.discover_plugins()
    for m in manifests:
        if m.name == plugin_name and m.base_path:
            env_path = m.base_path / ".env"
            if env_path.is_file():
                values = dotenv_values(env_path)
                for key, val in values.items():
                    # Only set if not already in environment (env > plugin .env)
                    if key not in os.environ and val is not None:
                        os.environ[key] = val
            break


@dataclass
class AgentComponents:
    """Result of setting up the agent runtime components."""

    runner: AgentRunner
    registry: ToolRegistry
    skill_registry: SkillRegistry
    config: MrLangConfig
    system_prompt: str
    manifests: list[PluginManifest]
    store: BaseStore | None = None


async def setup_agent(
    workspace: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    extra_middleware: list[BaseMiddleware] | None = None,
    load_plugins: bool = True,
    plugin_name: str | None = None,
) -> AgentComponents:
    """Wire up workspace, model, tools, plugins, and graph into an AgentRunner.

    This is the shared setup used by chat, serve, and telegram CLI commands.

    Args:
        plugin_name: If given, only activate this plugin's tools/skills/workspace
            for workspace isolation. Other plugins are discovered but not activated.
    """
    # If a plugin is targeted, load its .env into the environment BEFORE creating
    # the config object. This way pydantic-settings picks up the plugin's
    # MR_LANG_DEFAULT_PROVIDER / MR_LANG_DEFAULT_MODEL / OLLAMA_BASE_URL, etc.
    if plugin_name:
        _load_plugin_env(plugin_name)

    config = MrLangConfig()

    # Load workspace
    system_prompt = "You are a helpful assistant."
    if workspace:
        ws = load_workspace(workspace)
        system_prompt = build_system_prompt(ws)
        console.print(f"[green]Loaded workspace:[/green] {workspace}")

    # Resolve model
    provider = provider or config.default_provider
    model = model or config.default_model
    model_kwargs: dict = {}
    if provider == "ollama" and config.ollama_base_url:
        model_kwargs["base_url"] = config.ollama_base_url
    chat_model = get_chat_model(provider, model, **model_kwargs)
    console.print(f"[green]Model:[/green] {provider}/{model}")

    # Configure tool safety
    allowed_paths = config.get_tools_allowed_paths()
    if allowed_paths:
        set_allowed_paths(allowed_paths)
        console.print(f"[yellow]Filesystem sandbox:[/yellow] {len(allowed_paths)} allowed path(s)")
    set_blocked_commands(config.get_tools_blocked_commands())

    # Register builtin tools
    registry = ToolRegistry()
    for t in [read_file, write_file, list_files, run_shell]:
        registry.register(t)

    # Discover and activate plugins
    skill_registry = SkillRegistry()
    manifests: list[PluginManifest] = []
    if load_plugins:
        manifests = PluginLoader.discover_plugins()
        if plugin_name:
            # Isolated mode: only activate the target plugin
            target = [m for m in manifests if m.name == plugin_name]
            if target:
                await load_plugins_into_registries(registry, skill_registry, manifests=target)
                console.print(f"[green]Plugin (isolated):[/green] {plugin_name}")
            else:
                console.print(f"[yellow]Plugin '{plugin_name}' not found[/yellow]")
        else:
            # Load all plugins (general-purpose mode)
            await load_plugins_into_registries(registry, skill_registry, manifests=manifests)
    if registry.names():
        console.print(f"[green]Tools:[/green] {', '.join(registry.names())}")

    # Inject skills into system prompt
    if skill_registry.list():
        active_skills: list[str] = []
        for skill in skill_registry.list():
            try:
                validate_skill_requirements(skill, registry)
                system_prompt += "\n\n" + skill_to_prompt_section(skill)
                active_skills.append(skill.name)
            except SkillError as e:
                console.print(f"[yellow]Skill '{skill.name}' skipped:[/yellow] {e}")
        if active_skills:
            console.print(f"[green]Skills:[/green] {', '.join(active_skills)}")

    # Set up memory (checkpointer for conversation history, store for long-term memory)
    # Each plugin gets its own database folder under .mr_lang/db/<plugin>/
    checkpointer_kwargs: dict = {}
    store_kwargs: dict = {}
    if config.memory_backend == "sqlite":
        if plugin_name:
            db_dir = Path(".mr_lang") / "db" / plugin_name
        else:
            db_dir = Path(".mr_lang") / "db" / "default"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "mr_lang.db"
        checkpointer_kwargs["path"] = str(db_path)
        store_kwargs["path"] = str(db_path)
    elif config.memory_backend == "postgres":
        checkpointer_kwargs["url"] = config.postgres_url
        store_kwargs["url"] = config.postgres_url

    # Create embeddings for semantic memory search
    embeddings = None
    if config.memory_enabled:
        try:
            from mr_lang.providers.embeddings import get_embeddings

            embed_kwargs: dict = {}
            if config.embedding_provider == "ollama" and config.ollama_base_url:
                embed_kwargs["base_url"] = config.ollama_base_url
            embeddings = get_embeddings(
                config.embedding_provider, config.embedding_model, **embed_kwargs
            )
        except Exception as e:
            console.print(f"[yellow]Embeddings unavailable ({e}), memory search disabled[/yellow]")

    checkpointer = await get_checkpointer(config.memory_backend, **checkpointer_kwargs)
    store = await get_store(config.memory_backend, embed=embeddings, **store_kwargs)
    console.print(f"[green]Memory:[/green] {config.memory_backend}")

    # Register memory tools (namespace-scoped per plugin)
    if config.memory_enabled:
        from mr_lang.tools.builtin.memory import create_memory_tools

        ns_prefix = (plugin_name or "default",)
        memory_tools = create_memory_tools(store, namespace_prefix=ns_prefix)
        for t in memory_tools:
            registry.register(t)
        console.print(f"[green]Memory tools:[/green] namespace={ns_prefix[0]}")

    # Register RAG tools if the active plugin has [plugin.rag] config
    active_manifest = None
    if plugin_name:
        active_manifest = next((m for m in manifests if m.name == plugin_name), None)
    if active_manifest and active_manifest.rag and embeddings:
        try:
            from mr_lang.tools.builtin.rag import create_rag_tools

            rag_cfg = active_manifest.rag
            persist_dir = str(
                (active_manifest.base_path / rag_cfg.persist_dir).resolve()
                if active_manifest.base_path
                else rag_cfg.persist_dir
            )

            if rag_cfg.backend == "chroma":
                from langchain_chroma import Chroma

                vector_store = Chroma(
                    persist_directory=persist_dir,
                    embedding_function=embeddings,
                    collection_name=plugin_name or "default",
                )
            elif rag_cfg.backend == "faiss":
                from langchain_community.vectorstores import FAISS

                vector_store = FAISS.from_texts([""], embedding=embeddings)
            else:
                console.print(f"[yellow]Unknown RAG backend: {rag_cfg.backend}[/yellow]")
                vector_store = None

            if vector_store:
                rag_tools = create_rag_tools(vector_store)
                for t in rag_tools:
                    registry.register(t)
                console.print(f"[green]RAG:[/green] {rag_cfg.backend} at {persist_dir}")
        except ImportError as e:
            console.print(f"[yellow]RAG unavailable: {e}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]RAG setup failed: {e}[/yellow]")

    # Build graph with middleware (observability is always on)
    collector = EventCollector()
    obs_mw = ObservabilityMiddleware(collector=collector, session_id="default")
    middleware: list[BaseMiddleware] = [LoggingMiddleware(), obs_mw]
    if extra_middleware:
        middleware.extend(extra_middleware)
    graph = build_agent_graph(
        model=chat_model,
        tools=registry.list(),
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        store=store,
        middleware=middleware,
    )
    runner = AgentRunner(graph, middleware=middleware)

    return AgentComponents(
        runner=runner,
        registry=registry,
        skill_registry=skill_registry,
        config=config,
        system_prompt=system_prompt,
        manifests=manifests,
        store=store,
    )
