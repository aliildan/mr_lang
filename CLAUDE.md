# mr_lang

Custom agent orchestration framework built on LangChain/LangGraph/LangSmith. Replaces OpenClaw runtime with open-source LangChain ecosystem while preserving the same developer patterns: Markdown skills, workspace configs, tool registries, CLI-first interaction, and pluggable model providers.

## Architecture

- **Runtime**: LangGraph StateGraph with checkpointing + long-term store
- **CLI**: Typer-based (`mr-lang`), primary interaction mode
- **Skills**: Markdown files with YAML frontmatter, injected into system prompt at runtime
- **Tools**: Python functions with `@tool` decorator, auto-discovered from registries
- **Workspace**: IDENTITY.md, SOUL.md, USER.md, TOOLS.md, AGENTS.md — defines agent personality
- **Providers**: Pluggable via `init_chat_model("provider:model")` — Ollama, OpenAI, Anthropic, etc.
- **Adapters**: Telegram bot, MCP server/client

## Project Structure

```
src/mr_lang/
  config.py              # MrLangConfig (Pydantic settings)
  exceptions.py          # MrLangError hierarchy
  core/
    state.py             # AgentState TypedDict for LangGraph
    graph.py             # build_agent_graph() — central runtime engine
    registry.py          # ToolRegistry, SkillRegistry
    runner.py            # AgentRunner — high-level run/stream
  cli/                   # Typer commands (chat, agents, tools, skills, config)
  skills/                # Skill loader, schema, executor
  tools/                 # Tool discovery + builtin tools (filesystem, shell, web)
  workspace/             # Workspace loader, schema, prompt builder
  providers/             # Model provider wrappers
  adapters/
    telegram/            # Telegram bot adapter
    mcp/                 # MCP server (expose) + client (consume)
  memory/                # Checkpointer + store wrappers
  middleware/            # Before/after model hooks
tests/
examples/
  workspaces/            # Example workspace configs
  skills/                # Example skill definitions
```

## Conventions

- **Python 3.11+**, type hints everywhere
- **Async-first**: all agent execution is async
- **Pydantic v2** for config/state schemas
- **TypedDict** for LangGraph state (not Pydantic — LangGraph requirement)
- **ruff** for linting and formatting (line-length 100)
- **pytest** + pytest-asyncio for tests
- **snake_case** for tool names, agent names, module names
- Errors use structured exceptions inheriting from `MrLangError`
- CLI output: stderr for human-readable, stdout for structured (JSON)
- Environment variables prefixed with `MR_LANG_` for framework config
- Config layering: defaults → mr_lang.toml → ~/.config/mr_lang/config.toml → env vars → CLI flags

## Key Concepts

### Workspace
A directory containing Markdown files that define an agent's personality and capabilities:
- `IDENTITY.md` — Who the agent is (name, role, language)
- `SOUL.md` — Personality, teaching style, behavioral rules
- `USER.md` — Information about the target user
- `TOOLS.md` — Available tools and system capabilities
- `AGENTS.md` — Sub-agent definitions

### Skill
A Markdown file (`*.SKILL.md`) with YAML frontmatter declaring requirements and a body containing instructions. Skills are NOT tools — they are prompt injections that get appended to the system message when activated, optionally with associated tool sets.

### Tool
A Python function decorated with `@tool` from langchain. Registered in the ToolRegistry for discovery and use by agents.

### Adapter
A module that connects mr_lang agents to external interfaces (Telegram, MCP, HTTP API).

## Development

```bash
# Install in dev mode
pip install -e ".[all]"

# Run CLI
mr-lang --help
mr-lang chat --workspace ./examples/workspaces/simple

# Tests
pytest
pytest --cov=mr_lang

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Run Telegram bot
mr-lang telegram start --workspace ./examples/workspaces/simple

# Serve as MCP
mr-lang serve --mcp --workspace ./examples/workspaces/simple
```

## Dependencies

Core: langchain-core, langgraph, langsmith, typer, rich, pydantic, pydantic-settings, httpx, pyyaml, python-frontmatter

Optional: langchain-ollama, langchain-openai, langchain-anthropic, python-telegram-bot, fastmcp, psycopg, langgraph-checkpoint-postgres

Dev: pytest, pytest-asyncio, pytest-cov, ruff, mypy

## Related Projects

- **herr_molly** (`/Users/aildan/Projects/herr_molly/`) — Austrian school teaching assistant, will be migrated to mr_lang
