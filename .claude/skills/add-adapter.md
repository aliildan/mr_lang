---
name: add-adapter
description: Scaffold a new adapter module to connect mr_lang agents to external interfaces
---

# Add Adapter

Create a new adapter for the mr_lang framework. Adapters connect agents to external interfaces like messaging platforms, APIs, or protocols.

## Instructions

When the user asks to add a new adapter, follow these steps:

1. Ask for the adapter name and target platform if not provided
2. Create the adapter package at `src/mr_lang/adapters/<name>/`
3. Add a CLI command at `src/mr_lang/cli/<name>_cmd.py`
4. Add the command to `src/mr_lang/cli/app.py`

## Directory Structure

```
src/mr_lang/adapters/<name>/
  __init__.py          # Public API exports
  bot.py / adapter.py  # Main adapter class
  handlers.py          # Message/event handlers
  sessions.py          # Session/thread management (if applicable)
```

## Adapter Class Template

```python
"""<Platform> adapter for mr_lang agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mr_lang.exceptions import AdapterError

if TYPE_CHECKING:
    from mr_lang.core.runner import AgentRunner


class <Name>Adapter:
    """Connects mr_lang agents to <platform>."""

    def __init__(self, runner: AgentRunner, **kwargs) -> None:
        self.runner = runner

    async def start(self) -> None:
        """Start the adapter (connect, listen for events)."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Gracefully stop the adapter."""
        raise NotImplementedError

    async def handle_message(self, message: str, session_id: str) -> str:
        """Route an incoming message to the agent and return the response."""
        result = await self.runner.run(message=message, thread_id=session_id)
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            return last.content if hasattr(last, "content") else str(last)
        return ""
```

## CLI Command Template

```python
# src/mr_lang/cli/<name>_cmd.py
"""CLI entrypoint for the <Name> adapter."""

from __future__ import annotations

from rich.console import Console

from mr_lang.cli.setup import setup_agent

console = Console(stderr=True)


async def run_<name>(
    workspace: str | None = None,
    provider: str = "ollama",
    model: str = "llama3",
    plugin: str | None = None,
) -> None:
    """Wire up workspace/provider/graph/runner and start the adapter."""
    components = await setup_agent(
        workspace=workspace,
        provider=provider,
        model=model,
        plugin_name=plugin,
    )
    # Create and start your adapter here
```

Register in `app.py`:

```python
@app.command()
def <name>(
    workspace: str = typer.Option(None, "--workspace", "-w"),
    provider: str = typer.Option("ollama", "--provider", "-p"),
    model: str = typer.Option("llama3", "--model", "-m"),
    plugin: str = typer.Option(None, "--plugin"),
) -> None:
    """Start the <Name> adapter."""
    import asyncio
    from mr_lang.cli.<name>_cmd import run_<name>
    asyncio.run(run_<name>(workspace=workspace, provider=provider,
                           model=model, plugin=plugin))
```

## Rules

- Adapter MUST accept an `AgentRunner` — it delegates all agent logic to the runner
- Use `setup_agent()` from `mr_lang.cli.setup` to wire up everything (it handles plugins, tools, skills, memory, middleware)
- Session management maps external user IDs to LangGraph thread_ids
- If the adapter needs skills (for command menus), use `components.skill_registry.list()`
- Add optional dependency to `pyproject.toml` under `[project.optional-dependencies]`
- Handle graceful shutdown (SIGINT/SIGTERM)
- Support `--plugin` flag for workspace isolation
- Use the `AdapterError` exception class for adapter-specific errors
- Follow the Telegram adapter as a reference implementation
