"""Interactive chat REPL."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown

from mr_lang.config import MrLangConfig
from mr_lang.core.graph import build_agent_graph
from mr_lang.core.registry import ToolRegistry
from mr_lang.core.runner import AgentRunner
from mr_lang.middleware.logging_mw import LoggingMiddleware
from mr_lang.observability.collector import EventCollector
from mr_lang.observability.middleware import ObservabilityMiddleware
from mr_lang.providers.base import get_chat_model
from mr_lang.tools.builtin import list_files, read_file, run_shell, write_file
from mr_lang.workspace.builder import build_system_prompt
from mr_lang.workspace.loader import load_workspace

console = Console(stderr=True)


async def run_chat(
    workspace: str | None = None,
    provider: str = "ollama",
    model: str = "llama3",
) -> None:
    """Run the interactive chat loop."""
    config = MrLangConfig()

    # Load workspace if provided
    system_prompt = "You are a helpful assistant."
    if workspace:
        ws = load_workspace(workspace)
        system_prompt = build_system_prompt(ws)
        console.print(f"[green]Loaded workspace:[/green] {workspace}")

    # Set up model
    provider = provider or config.default_provider
    model = model or config.default_model
    chat_model = get_chat_model(provider, model)
    console.print(f"[green]Model:[/green] {provider}/{model}")

    # Set up tools
    registry = ToolRegistry()
    builtin_tools = [read_file, write_file, list_files, run_shell]
    for t in builtin_tools:
        registry.register(t)

    # Discover and activate plugins (tools, skills, MCP servers)
    from mr_lang.core.registry import SkillRegistry
    from mr_lang.plugins.integrations import load_plugins_into_registries

    skill_registry = SkillRegistry()
    await load_plugins_into_registries(registry, skill_registry)
    if registry.names():
        console.print(f"[green]Tools:[/green] {', '.join(registry.names())}")

    # Build graph with middleware
    thread_id = "cli-session"
    collector = EventCollector()
    obs_mw = ObservabilityMiddleware(collector=collector, session_id=thread_id)
    middleware = [LoggingMiddleware(), obs_mw]
    graph = build_agent_graph(
        model=chat_model,
        tools=registry.list(),
        system_prompt=system_prompt,
        middleware=middleware,
    )
    runner = AgentRunner(graph)
    console.print("[dim]Type 'quit' or 'exit' to end. 'clear' to reset.[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold cyan]you>[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("quit", "exit"):
            console.print("[dim]Goodbye![/dim]")
            break
        if user_input.strip().lower() == "clear":
            thread_id = f"cli-session-{id(object())}"
            console.print("[dim]Conversation cleared.[/dim]")
            continue

        try:
            result = await runner.run(message=user_input, thread_id=thread_id)
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                content = last.content if hasattr(last, "content") else str(last)
                console.print()
                console.print(Markdown(content))
                console.print()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
