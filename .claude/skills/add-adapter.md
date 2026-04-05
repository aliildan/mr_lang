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
3. Add a CLI command at `src/mr_lang/cli/<name>.py` if the adapter needs a CLI entry point

## Directory Structure

```
src/mr_lang/adapters/<name>/
  __init__.py          # Public API exports
  adapter.py           # Main adapter class
  handlers.py          # Message/event handlers
  sessions.py          # Session/thread management (if applicable)
```

## Adapter Class Template

```python
"""<Platform> adapter for mr_lang agents."""

from __future__ import annotations

from mr_lang.core.runner import AgentRunner


class <Name>Adapter:
    """Connects mr_lang agents to <platform>."""

    def __init__(self, runner: AgentRunner, **kwargs):
        self.runner = runner

    async def start(self) -> None:
        """Start the adapter (connect, listen for events)."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Gracefully stop the adapter."""
        raise NotImplementedError

    async def handle_message(self, message: str, session_id: str) -> str:
        """Route an incoming message to the agent and return the response."""
        result = await self.runner.run(
            input=message,
            thread_id=session_id,
        )
        return result
```

## Rules

- Adapter MUST accept an `AgentRunner` — it delegates all agent logic to the runner
- Session management maps external user IDs to LangGraph thread_ids
- Add optional dependency to `pyproject.toml` under `[project.optional-dependencies]`
- Add CLI command: `mr-lang <adapter> start --workspace <path>`
- Handle graceful shutdown (SIGINT/SIGTERM)
- Media handling (images, files) should convert to formats the agent tools can process
