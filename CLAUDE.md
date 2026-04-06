# mr_lang

Custom agent orchestration framework built on LangChain/LangGraph/LangSmith. Provides reusable infrastructure for building AI agents with Markdown-driven personalities, pluggable model providers, and multiple deployment targets.

## Architecture

- **Runtime**: LangGraph ReAct agent with middleware pipeline, checkpointing, and long-term store
- **CLI**: Typer-based (`mr-lang`), primary interaction mode
- **Skills**: Markdown files with YAML frontmatter, injected into system prompt at runtime (not tools)
- **Tools**: Python functions with `@tool` decorator, auto-discovered from registries
- **Workspace**: IDENTITY.md, SOUL.md, USER.md, TOOLS.md, AGENTS.md — defines agent personality
- **Providers**: Pluggable model backends — Ollama (local or cloud), OpenAI, Anthropic
- **Adapters**: Telegram bot (with per-plugin auth/invite system), MCP server/client
- **Plugins**: TOML-manifest based extension system with project scaffolding, interactive wizard, and workspace isolation
- **Memory**: 3-layer architecture — conversation checkpointer, semantic store (LangGraph Store), per-plugin RAG
- **Observability**: JSONL-based local event logging with 7 event types and monitoring CLI

## Project Structure

```
src/mr_lang/
  __init__.py
  config.py                # MrLangConfig (Pydantic BaseSettings, MR_LANG_ prefix)
  exceptions.py            # MrLangError hierarchy (7 exception types)
  core/
    state.py               # AgentState TypedDict for LangGraph
    graph.py               # build_agent_graph() — ReAct agent with middleware + human-in-the-loop
    registry.py            # ToolRegistry, SkillRegistry
    runner.py              # AgentRunner — run/stream/stream_tokens interface
  cli/
    app.py                 # Typer app entry point with subcommands
    setup.py               # Shared setup logic for all CLI commands (plugin isolation)
    chat.py                # Interactive REPL with token streaming
    telegram_cmd.py        # Telegram bot launcher (per-plugin resolution)
    serve_cmd.py           # MCP server launcher
    init_cmd.py            # Interactive project wizard (mr-lang init)
    plugin_cmd.py          # Plugin management (list, activate, capabilities)
    monitor_cmd.py         # CLI observability (sessions, events, live tail, JSON)
    rag_cmd.py             # Index files into plugin RAG knowledge base
    doctor_cmd.py          # Diagnose common setup issues
  skills/
    schema.py              # SkillDefinition model
    loader.py              # Parse *.SKILL.md with frontmatter
    executor.py            # Validate requirements + inject into system prompt
  tools/
    discovery.py           # Auto-discover tools from entry points
    builtin/
      filesystem.py        # read_file, write_file, list_files (with sandbox)
      shell.py             # run_shell (subprocess with timeout + blocklist)
      web.py               # http_request (httpx)
      memory.py            # remember_fact, recall_facts, forget_fact (namespace-scoped)
      rag.py               # search_knowledge, add_to_knowledge (per-plugin vector store)
  workspace/
    schema.py              # Workspace model
    loader.py              # Load IDENTITY/SOUL/USER/TOOLS/AGENTS.md
    builder.py             # Build system prompt from workspace
  providers/
    base.py                # get_chat_model() factory for ollama/openai/anthropic
    embeddings.py          # get_embeddings() factory for ollama/openai
  adapters/
    telegram/
      bot.py               # TelegramBot — lifecycle + dynamic skill commands
      handlers.py          # Command, message, and skill handlers with auth
      auth.py              # AuthGuard — invite codes, allowlist, admin roles
      sessions.py          # SessionManager — per-user thread IDs
    mcp/
      server.py            # McpServer — expose agent + tools as MCP
      client.py            # load_mcp_tools() — consume remote MCP servers
  memory/
    checkpointer.py        # LangGraph checkpointer factory (memory/sqlite/postgres)
    store.py               # LangGraph store factory with embedding support
  middleware/
    base.py                # Middleware Protocol (model, tool, run, error hooks)
    logging_mw.py          # Timing, token usage, tool call logging
    rate_limit.py          # Token-bucket rate limiting
    summarization.py       # Auto-summarize long conversations
    langsmith_mw.py        # LangSmith env var bridge
  observability/
    events.py              # EventType enum, ObservabilityEvent schema
    collector.py           # JSONL event writer with session queries
    middleware.py           # ObservabilityMiddleware (all 7 event types)
  api/
    routes.py              # REST API for sessions/events (aiohttp)
    dashboard.py           # Single-page HTML dashboard (inline JS/CSS)
  plugins/
    schema.py              # PluginManifest + TelegramConfig + MemoryConfig + RagConfig
    loader.py              # PluginLoader — discover + activate from TOML manifests
    scaffold.py            # scaffold_project() + WizardConfig
    integrations.py        # load_plugins_into_registries() helper
tests/
  adapters/                # Telegram (sessions, auth), MCP server
  core/                    # Registry
  middleware/              # Logging middleware
  observability/           # Event collector
  plugins/                 # Loader, scaffold, env var expansion, telegram config
  skills/                  # Skill loader
  workspace/               # Workspace loader + builder
```

## Conventions

- **Python 3.11+**, type hints everywhere
- **Async-first**: all agent execution is async
- **Pydantic v2** for config/state schemas
- **TypedDict** for LangGraph state (not Pydantic — LangGraph requirement)
- **ruff** for linting and formatting (line-length 100)
- **pytest** + pytest-asyncio for tests
- **snake_case** for tool names, agent names, module names
- Errors use structured exceptions inheriting from `MrLangError`:
  `ConfigError`, `ProviderError`, `ToolError`, `SkillError`, `WorkspaceError`, `PluginError`, `AdapterError`
- CLI output: stderr for human-readable (Rich), stdout for structured (JSON)
- Environment variables prefixed with `MR_LANG_` for framework config
- Config layering: defaults -> mr_lang.toml -> ~/.config/mr_lang/config.toml -> env vars -> CLI flags
- Sensitive config fields use `repr=False` to prevent leaking in logs
- Plugins use warn-not-crash pattern: failed plugin loads log warnings, don't halt the app

## Key Concepts

### Workspace
A directory containing Markdown files that define an agent's personality and capabilities:
- `IDENTITY.md` — Who the agent is (name, role, language) **[required]**
- `SOUL.md` — Personality, teaching style, behavioral rules
- `USER.md` — Information about the target user
- `TOOLS.md` — Available tools and system capabilities
- `AGENTS.md` — Sub-agent definitions and model config

### Skill
A Markdown file (`*.SKILL.md`) with YAML frontmatter declaring requirements and a body containing instructions. Skills are NOT tools — they are prompt injections appended to the system message when activated, optionally with associated tool sets.

### Plugin
A standalone project with a `mr_lang_plugin.toml` manifest. Plugins can provide tools, skills, workspaces, and MCP server connections. Created under `./plugins/` by `mr-lang init`. Discovered via entry points, cwd, `./plugins/` subdirectories, or `MR_LANG_PLUGINS` env var.

#### Plugin Isolation
When `--plugin <name>` is passed to `chat`, `serve`, or `telegram` commands, only that plugin's tools, skills, and workspace are activated. Other plugins are discovered but not loaded into the agent runtime, preventing cross-plugin context leakage.

#### Per-Plugin Telegram Config
Plugins declare their own Telegram config in `mr_lang_plugin.toml`:
```toml
[plugin.telegram]
bot_token = "${MY_PLUGIN_TELEGRAM_TOKEN}"
auth_mode = "invite"
admin_user_ids = [12345]
allowed_user_ids = [12345]
invite_codes = []
max_uses_per_code = 0
```

Bot tokens support `${ENV_VAR}` syntax with 3-tier resolution: os.environ → plugin's `.env` → project `.env`.

### Memory & RAG
The framework provides three memory layers:
1. **Conversation memory** (checkpointer) — per-thread message history, survives restarts with `sqlite` backend
2. **Semantic memory** (LangGraph Store) — long-term facts via `remember_fact`/`recall_facts`/`forget_fact` tools, with embedding-based semantic search. Namespace-scoped per plugin.
3. **Knowledge base** (RAG) — per-plugin vector store for documents/textbooks via `search_knowledge`/`add_to_knowledge` tools

Memory tools are namespace-isolated: the prefix `(plugin_name,)` is hardcoded at registration time, so the LLM cannot access other plugins' memory.

Plugin manifest config:
```toml
[plugin.memory]
enabled = true
embedding_model = "nomic-embed-text"

[plugin.rag]
backend = "chroma"        # chroma or faiss
persist_dir = "./.rag_data"
chunk_size = 1000
chunk_overlap = 200
```

### Tool Safety
- **Filesystem sandbox**: `MR_LANG_TOOLS_ALLOWED_PATHS` — comma-separated list of allowed directories. When set, `read_file`/`write_file`/`list_files` reject paths outside allowed roots. Off by default.
- **Shell blocklist**: `MR_LANG_TOOLS_BLOCKED_COMMANDS` — comma-separated patterns. Default: `rm -rf /,mkfs,dd if=,:(){ :|:& };:`

### Adapter
A module connecting mr_lang agents to external interfaces. Current adapters:
- **Telegram**: Bot with invite-code auth, admin commands, photo support (per-plugin config)
- **MCP**: Server (expose tools) and Client (consume remote MCP tools)

## Development

```bash
# Install in dev mode
pip install -e ".[all]"

# Run CLI
mr-lang --help
mr-lang chat --workspace ./examples/workspaces/simple
mr-lang chat --plugin my-plugin  # isolated to plugin context

# Tests
pytest
pytest --cov=mr_lang

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Create a new plugin project
mr-lang init

# Run Telegram bot (per-plugin)
mr-lang telegram --plugin my-plugin
mr-lang telegram --workspace ./examples/workspaces/simple

# Serve as MCP server
mr-lang serve --workspace ./examples/workspaces/simple
mr-lang serve --plugin my-plugin

# Index documents into a plugin's knowledge base (RAG)
mr-lang rag --plugin my-plugin ./docs/

# Monitor sessions
mr-lang monitor --session <session-id>
mr-lang monitor --tail
mr-lang monitor --json

# Web dashboard
mr-lang dashboard

# Diagnose setup issues
mr-lang doctor

# Show current config
mr-lang config
```

## Configuration

All config via `MR_LANG_` prefixed env vars or `.env` file. See `.env.example` for the full list.

Key variables:
- `MR_LANG_DEFAULT_PROVIDER` / `MR_LANG_DEFAULT_MODEL` — model selection
- `MR_LANG_OLLAMA_BASE_URL` — for cloud Ollama instances
- `MR_LANG_TELEGRAM_BOT_TOKEN` — fallback Telegram token (prefer per-plugin `[plugin.telegram]`)
- `MR_LANG_TELEGRAM_AUTH_MODE` — `open`, `allowlist`, or `invite`
- `MR_LANG_TELEGRAM_ADMIN_USER_IDS` — comma-separated admin Telegram IDs
- `MR_LANG_PLUGINS` — colon-separated plugin directories
- `MR_LANG_MEMORY_BACKEND` — `memory` (default), `sqlite`, or `postgres`
- `MR_LANG_MEMORY_ENABLED` — enable/disable agent memory tools (default: true)
- `MR_LANG_EMBEDDING_PROVIDER` / `MR_LANG_EMBEDDING_MODEL` — embedding config for semantic search
- `MR_LANG_TOOLS_ALLOWED_PATHS` — filesystem sandbox paths (comma-separated)
- `MR_LANG_TOOLS_BLOCKED_COMMANDS` — shell blocklist patterns (comma-separated)

## Dependencies

Core: langchain-core, langgraph, langsmith, typer, rich, pydantic, pydantic-settings, httpx, pyyaml, python-frontmatter

Optional extras: `[ollama]`, `[openai]`, `[anthropic]`, `[telegram]`, `[mcp]`, `[postgres]`, `[dev]`, `[all]`
