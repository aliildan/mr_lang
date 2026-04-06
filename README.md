# mr_lang

**Build AI agents with personality, memory, and real tools — deploy as CLI, Telegram bot, or MCP server.**

mr_lang is a Python framework built on [LangChain](https://www.langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/). You define your agent in Markdown, give it tools and skills, and run it anywhere.

---

## Quick Start

```bash
# Install
git clone https://github.com/aildan/mr-lang.git && cd mr-lang
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[ollama,dev]"

# Create your first agent — the wizard asks what you need
mr-lang init

# Run it
pip install -e plugins/<plugin-name>
mr-lang chat --plugin <plugin-name>
```

---

## What Can You Build?

| Example | Features Used |
|---------|--------------|
| A **math tutor** that speaks German, remembers student progress, and references textbook content | Workspace, memory, RAG, skills |
| A **code review bot** on Telegram with invite-code access control | Workspace, tools, Telegram adapter |
| A **support agent** that looks up orders via custom tools and files tickets | Workspace, custom tools, MCP server |
| A **personal assistant** that remembers your preferences across sessions | Workspace, memory |

Each of these is a **plugin** — a self-contained project with its own personality, tools, skills, and config.

---

## The Wizard

`mr-lang init` walks you through creating a plugin step by step. You pick only what you need — the generated project matches your answers:

| Step | What It Asks | What It Generates |
|------|-------------|-------------------|
| **Name & About** | Project name, description, author | `mr_lang_plugin.toml`, `pyproject.toml` |
| **Personality** | Agent name, role, language, tone | `workspace/IDENTITY.md`, `SOUL.md` |
| **Provider** | Ollama / OpenAI / Anthropic, model name | `workspace/AGENTS.md`, `.env` |
| **Memory** | Enable remember/recall/forget tools? | `[plugin.memory]` in manifest, memory tools in `TOOLS.md` |
| **RAG** | Enable document search? Backend? | `[plugin.rag]` in manifest, research skill, RAG tools in `TOOLS.md` |
| **Telegram** | Enable bot? Token, auth mode, admin IDs | `[plugin.telegram]` in manifest, token in `.env` |
| **MCP** | Connect to external MCP servers? | `[plugin.mcp]` in manifest |

No templates — just questions. Enable what you need, skip what you don't. Everything can be changed later by editing the generated files.

---

## How It Works

### 1. Workspace — Define Personality in Markdown

A workspace is a folder of Markdown files that shape your agent:

```
workspace/
  IDENTITY.md    # Name, role, language
  SOUL.md        # Personality, tone, behavioral rules
  USER.md        # Target audience and their preferences
  TOOLS.md       # What tools are available and how to use them
  AGENTS.md      # Model provider and config
```

No Python needed to define personality — just Markdown. Example `IDENTITY.md`:

```markdown
# Identity

- **Name**: Herr Molly
- **Role**: Math tutor for secondary school students
- **Language**: German
- **Version**: 0.1.0
```

### 2. Skills — Prompt Instructions as Markdown

Skills are Markdown files with YAML frontmatter. They get injected into the system prompt at runtime — think of them as "modes" the agent can follow.

```markdown
<!-- skills/tutoring.SKILL.md -->
---
name: tutoring
description: Help students learn through guided questions
emoji: "🎓"
requires:
  tools: [read_file]
tags: [teaching]
---

# Tutoring Mode

When helping with homework:
1. Ask what topic they're working on
2. Have them explain what they've tried
3. Guide with questions — never give the answer directly
```

In Telegram, skills automatically show up as `/` commands in the menu.

### 3. Tools — Python Functions the Agent Can Call

Tools use LangChain's `@tool` decorator and are auto-discovered from your plugin:

```python
# src/my_plugin/tools/__init__.py
from langchain_core.tools import tool

@tool
def lookup_student(student_id: str) -> str:
    """Look up a student's profile and recent grades."""
    return f"Student {student_id}: Grade A in Math, B in Science"
```

### 4. Deploy

```bash
mr-lang chat --plugin <plugin-name>                       # CLI (development)
mr-lang telegram --plugin <plugin-name>                   # Telegram bot (users)
mr-lang serve --plugin <plugin-name> --host 0.0.0.0       # MCP server (other AI tools)
```

---

## Plugin System

Every agent project is a **plugin** with a `mr_lang_plugin.toml` manifest:

```toml
[plugin]
name = "herr-molly"
version = "0.1.0"
description = "A German math tutor"

[plugin.paths]
workspace = "./workspace"
skills = "./src/herr_molly/skills"
tools_module = "herr_molly.tools"

[plugin.telegram]                                     # Optional
bot_token = "${HERR_MOLLY_TELEGRAM_TOKEN}"            # reads from .env
auth_mode = "invite"
admin_user_ids = [123456789]

[plugin.memory]                                       # Optional
enabled = true
embedding_model = "nomic-embed-text"

[plugin.rag]                                          # Optional
backend = "chroma"
persist_dir = "./.rag_data"
```

**Plugin isolation**: `--plugin herr-molly` loads only that plugin's tools, skills, and workspace. Other plugins can't see each other's memory or context.

**Discovery**: Plugins are found from (in order):
1. pip-installed entry points (`mr_lang.plugins` group)
2. `mr_lang_plugin.toml` in the current directory
3. Each subdirectory of `./plugins/` (the default location for `mr-lang init`)
4. Colon-separated paths in the `MR_LANG_PLUGINS` environment variable

---

## Memory & Knowledge

Three layers of memory, each serving a different purpose:

| Layer | Purpose | Persistence | How It Works |
|-------|---------|-------------|--------------|
| **Conversation** | Current chat thread | In-memory or SQLite | LangGraph checkpointer. Set `MR_LANG_MEMORY_BACKEND=sqlite` to survive restarts |
| **Semantic memory** | Facts about users | Embedding-based store | Agent calls `remember_fact` / `recall_facts`. Namespace-isolated per plugin |
| **Knowledge base** | Documents, textbooks | Chroma / FAISS vector store | Agent calls `search_knowledge`. Per-plugin, configured in `[plugin.rag]` |

Each plugin gets its own isolated database under `.mr_lang/db/<plugin-name>/`.

Example of how the agent uses memory:

```
User: "My name is Ali and I prefer Python examples"
Agent: [calls remember_fact(key="user_name", fact="Ali")]
Agent: [calls remember_fact(key="code_pref", fact="Prefers Python examples")]
Agent: "Got it, Ali! I'll use Python examples."

# New session, days later:
User: "Show me how sorting works"
Agent: [calls recall_facts(query="user preferences")]
Agent: "Here's a Python bubble sort example, Ali..."
```

### RAG — Adding Knowledge to Your Agent

Give your agent domain-specific knowledge by indexing documents into its knowledge base.

**1. Enable RAG in your plugin** (the wizard asks this, or add manually):

```toml
# mr_lang_plugin.toml
[plugin.rag]
backend = "chroma"
persist_dir = "./.rag_data"
chunk_size = 1000
chunk_overlap = 200
```

**2. Install the vector store backend:**

```bash
pip install langchain-chroma langchain-text-splitters
# or for FAISS:
pip install langchain-community faiss-cpu langchain-text-splitters
```

**3. Index your documents:**

```bash
# Index a single file
mr-lang rag --plugin <plugin-name> ./textbook.pdf

# Index an entire directory (finds .txt, .md, .pdf, .html, .rst recursively)
mr-lang rag --plugin <plugin-name> ./docs/

# Multiple sources at once
mr-lang rag --plugin <plugin-name> ./notes.md ./lectures/ ./references/

# Custom chunk size for fine-grained retrieval
mr-lang rag --plugin <plugin-name> --chunk-size 500 --chunk-overlap 100 ./docs/
```

**4. The agent can now search and cite the indexed content:**

```
User: "What does chapter 3 say about quadratic equations?"
Agent: [calls search_knowledge(query="quadratic equations")]
Agent: "According to the textbook, a quadratic equation has the form ax² + bx + c = 0..."
```

The agent can also add knowledge on the fly during conversation via the `add_to_knowledge` tool — just tell it to remember a document or reference.

Indexed data persists in `plugins/<name>/.rag_data/` and survives restarts.

---

## Telegram Bot

### Config

Each plugin owns its bot token — no shared globals:

```toml
[plugin.telegram]
bot_token = "${MY_BOT_TELEGRAM_TOKEN}"
auth_mode = "invite"
admin_user_ids = [5829764960]
```

Token goes in `.env`:
```
MY_BOT_TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
```

### Access Control

| Mode | Who Can Chat |
|------|-------------|
| `open` | Anyone |
| `allowlist` | Only IDs in `allowed_user_ids` |
| `invite` | Users who redeem an invite code (admins generate with `/invite`) |

### Commands

| Built-in | Admin-only |
|----------|-----------|
| `/start` `/help` `/clear` | `/invite` `/allow <id>` `/revoke <id>` `/status` |

Skills are registered as Telegram `/` commands automatically — users see all capabilities in the command menu.

```bash
mr-lang telegram --plugin <plugin-name>
```

---

## Monitoring

mr_lang logs 7 event types: session start/end, model call start/end, tool call start/end, and errors.

```bash
mr-lang monitor                        # List recorded sessions
mr-lang monitor --session <id>         # Events for a session
mr-lang monitor --tail                 # Live-stream events
mr-lang monitor --json                 # JSON output for scripting

mr-lang dashboard                      # Web UI at http://localhost:8080/dashboard
mr-lang dashboard --port 9090          # Custom port
```

### Diagnostics

```bash
mr-lang doctor    # Checks Python, provider, plugins, Telegram token, dependencies
mr-lang config    # Dump current config as JSON
```

---

## Configuration

All framework config uses `MR_LANG_` prefixed env vars. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Default | What It Does |
|----------|---------|-------------|
| `MR_LANG_DEFAULT_PROVIDER` | `ollama` | `ollama`, `openai`, or `anthropic` |
| `MR_LANG_DEFAULT_MODEL` | `llama3` | Model name for the provider |
| `MR_LANG_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL (local or cloud) |
| `MR_LANG_MEMORY_BACKEND` | `memory` | `memory` (in-process, lost on restart), `sqlite` (recommended), `postgres` |
| `MR_LANG_MEMORY_ENABLED` | `true` | Enable `remember_fact`/`recall_facts`/`forget_fact` tools |
| `MR_LANG_EMBEDDING_PROVIDER` | `ollama` | Embedding provider for semantic search |
| `MR_LANG_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |
| `MR_LANG_TOOLS_ALLOWED_PATHS` | *(empty = all)* | Filesystem sandbox — comma-separated allowed dirs |
| `MR_LANG_TOOLS_BLOCKED_COMMANDS` | `rm -rf /,...` | Shell blocklist — comma-separated patterns |
| `MR_LANG_PLUGINS` | *(empty)* | Extra plugin directories — colon-separated |

---

## CLI Reference

| Command | What It Does |
|---------|-------------|
| `mr-lang init` | Scaffold a new plugin project (interactive wizard) |
| `mr-lang chat` | Interactive chat with token streaming |
| `mr-lang telegram` | Start Telegram bot for a plugin |
| `mr-lang serve` | Start MCP server |
| `mr-lang rag` | Index files into a plugin's knowledge base |
| `mr-lang plugin list` | List discovered plugins with capabilities |
| `mr-lang monitor` | View sessions, events, errors |
| `mr-lang dashboard` | Web-based monitoring UI |
| `mr-lang doctor` | Diagnose setup issues |
| `mr-lang config` | Show resolved configuration |
| `mr-lang tools` | List available tools |

All agent commands accept: `--workspace`, `--provider`, `--model`, `--plugin`.

---

## Development

```bash
pytest                         # Run tests
pytest --cov=mr_lang           # With coverage
ruff check src/ tests/         # Lint
ruff format src/ tests/        # Format
```

**Requirements**: Python 3.11+

**Core deps**: langchain-core, langgraph, langsmith, typer, rich, pydantic, pydantic-settings, httpx, pyyaml, python-frontmatter

**Optional extras**: `[ollama]` `[openai]` `[anthropic]` `[telegram]` `[mcp]` `[rag-chroma]` `[rag-faiss]` `[dashboard]` `[postgres]` `[dev]` `[all]`

## License

MIT
