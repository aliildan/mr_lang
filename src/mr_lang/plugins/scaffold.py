"""Scaffold new plugin projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mr_lang.exceptions import PluginError

# ---------------------------------------------------------------------------
# Workspace content fragments — assembled based on wizard answers
# ---------------------------------------------------------------------------

_SOUL_PLACEHOLDER = """\
# Personality

Be helpful, clear, and concise.
"""

_SOUL_RICH = """\
# Personality

## Communication Style
- Be friendly, clear, and helpful
- Use a conversational tone — not robotic, not overly casual
- Give concise answers by default, elaborate when asked
- Use bullet points and structure for complex answers

## Rules
- If you are unsure about something, say so honestly
- Ask clarifying questions rather than guessing
- When a task has multiple approaches, briefly explain the tradeoffs
- Stay focused on the user's request — do not add unrequested features
"""

_USER_PLACEHOLDER = """\
# User Profile

Adapt to the user's needs and preferences.
"""

_USER_RICH = """\
# User Profile

## Preferences
- Appreciates clear, structured answers
- Prefers concise responses with option to ask for more detail
"""

_SKILL_EXAMPLE = """\
---
name: example
description: An example skill
emoji: "💡"
requires:
  tools: []
  env: []
tags: [example]
---

# Example Skill

Demonstrate how to complete a simple task step by step.

1. Understand the request.
2. Break it into sub-steps.
3. Execute each sub-step.
4. Summarise the result.
"""

_SKILL_RESEARCH = """\
---
name: research
description: Research a topic using the knowledge base and memory
emoji: "🔍"
requires:
  tools: [search_knowledge, recall_facts]
  env: []
tags: [research, rag]
---

# Research

When the user asks about a topic:

1. Search the knowledge base with `search_knowledge` for relevant documents
2. Check memory with `recall_facts` for any prior context
3. Synthesize findings into a clear answer
4. Cite sources when using knowledge base content
5. Remember key findings with `remember_fact` for future reference
"""


def _pyproject_toml(name: str, module: str, description: str) -> str:
    return f"""\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.11"
dependencies = [
    "mr-lang>=0.1.0",
]

[project.entry-points."mr_lang.plugins"]
{name} = "{module}:get_plugin_manifest"

[tool.hatch.build.targets.wheel]
packages = ["src/{module}"]

[tool.ruff]
line-length = 100
target-version = "py311"
"""


def _manifest_toml(
    name: str,
    module: str,
    description: str,
    *,
    author: str = "",
    extra_deps: list[str] | None = None,
    mcp_servers: list[str] | None = None,
    telegram: TelegramWizardConfig | None = None,
    enable_memory: bool = False,
    enable_rag: bool = False,
    rag_backend: str = "chroma",
    embedding_model: str = "nomic-embed-text",
) -> str:
    deps = extra_deps or []
    deps_str = ", ".join(f'"{d}"' for d in deps)
    servers = mcp_servers or []
    servers_str = ", ".join(f'"{s}"' for s in servers)
    module_upper = module.upper()
    result = f"""\
[plugin]
name = "{name}"
version = "0.1.0"
description = "{description}"
author = "{author}"

[plugin.paths]
workspace = "./workspace"
skills = "./src/{module}/skills"
tools_module = "{module}.tools"

[plugin.mcp]
servers = [{servers_str}]

[plugin.cli]
module = ""

[plugin.dependencies]
packages = [{deps_str}]
"""
    if telegram is not None:
        admin_ids = ", ".join(str(i) for i in telegram.admin_user_ids)
        allowed_ids = ", ".join(str(i) for i in telegram.allowed_user_ids)
        result += f"""
[plugin.telegram]
bot_token = "${{{module_upper}_TELEGRAM_TOKEN}}"
auth_mode = "{telegram.auth_mode}"
admin_user_ids = [{admin_ids}]
allowed_user_ids = [{allowed_ids}]
invite_codes = []
max_uses_per_code = 0
"""
    if enable_memory:
        result += f"""
[plugin.memory]
enabled = true
embedding_model = "{embedding_model}"
"""
    if enable_rag:
        result += f"""
[plugin.rag]
backend = "{rag_backend}"
persist_dir = "./.rag_data"
chunk_size = 1000
chunk_overlap = 200
"""
    return result


def _init_py(module: str) -> str:
    return f'''\
"""Plugin package for {module}."""

from __future__ import annotations

from pathlib import Path

from mr_lang.plugins.schema import PluginManifest


def get_plugin_manifest() -> PluginManifest:
    """Return the plugin manifest (called by entry-point discovery)."""
    from mr_lang.plugins.loader import PluginLoader

    manifest_path = Path(__file__).resolve().parent.parent.parent / "mr_lang_plugin.toml"
    return PluginLoader.load_from_manifest(manifest_path)
'''


def _tools_init() -> str:
    # NOTE: avoid triple-quoted docstrings in the example code block below,
    # because nested triple-quotes break when embedded in a template string.
    lines = [
        '"""Custom tools for this plugin.',
        "",
        "Define LangChain @tool functions here. They will be auto-discovered",
        "when the plugin is activated. Example::",
        "",
        "    from langchain_core.tools import tool",
        "",
        "    @tool",
        '    def my_tool(query: str) -> str:',
        '        "Describe what this tool does -- this docstring is visible to the LLM."',
        '        return f"Result for {query}"',
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ]
    return "\n".join(lines)


_GITIGNORE = """\
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.env
.rag_data/
*.db
.venv/
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class TelegramWizardConfig:
    """Telegram-specific wizard answers."""

    bot_token: str = ""
    auth_mode: str = "invite"
    admin_user_ids: list[int] = field(default_factory=list)
    allowed_user_ids: list[int] = field(default_factory=list)


@dataclass
class WizardConfig:
    """All parameters the wizard can collect."""

    name: str = ""
    description: str = ""
    author: str = ""
    agent_name: str = ""
    agent_role: str = ""
    personality: str = ""
    language: str = "English"
    provider: str = "ollama"
    model: str = ""
    ollama_base_url: str = ""
    mcp_servers: list[str] = field(default_factory=list)
    enable_telegram: bool = False
    telegram: TelegramWizardConfig | None = None
    enable_memory: bool = False
    enable_rag: bool = False
    rag_backend: str = "chroma"
    embedding_model: str = "nomic-embed-text"


def scaffold_project(
    name: str,
    path: Path | None = None,
    description: str = "",
    wizard: WizardConfig | None = None,
) -> Path:
    """Create a new plugin project directory structure.

    Args:
        name: Plugin name (kebab-case, e.g. 'herr-molly').
        path: Parent directory in which to create the project. Defaults to cwd.
        description: Short project description.
        wizard: Optional wizard config with additional parameters.

    Returns:
        Path to the created project root.
    """
    base = (path or Path.cwd() / "plugins").resolve()
    base.mkdir(parents=True, exist_ok=True)
    project_root = base / name
    if project_root.exists():
        raise PluginError(f"Directory already exists: {project_root}")

    module = name.replace("-", "_")
    display_name = name.replace("-", " ").title()
    desc = description or f"A mr_lang plugin: {display_name}"
    wiz = wizard or WizardConfig()

    # Ensure telegram config exists when enabled
    if wiz.enable_telegram and wiz.telegram is None:
        wiz.telegram = TelegramWizardConfig()

    # Determine extra pip deps
    extra_deps: list[str] = []
    if wiz.enable_telegram:
        extra_deps.append("python-telegram-bot>=21")

    # Create directory tree
    src = project_root / "src" / module
    tools_dir = src / "tools"
    skills_dir = src / "skills"
    ws = project_root / "workspace"
    tests = project_root / "tests"

    for d in [tools_dir, skills_dir, ws, tests]:
        d.mkdir(parents=True)

    # Top-level files
    (project_root / "mr_lang_plugin.toml").write_text(
        _manifest_toml(
            name,
            module,
            desc,
            author=wiz.author,
            extra_deps=extra_deps,
            mcp_servers=wiz.mcp_servers,
            telegram=wiz.telegram if wiz.enable_telegram else None,
            enable_memory=wiz.enable_memory,
            enable_rag=wiz.enable_rag,
            rag_backend=wiz.rag_backend,
            embedding_model=wiz.embedding_model,
        ),
        encoding="utf-8",
    )
    (project_root / "pyproject.toml").write_text(
        _pyproject_toml(name, module, desc),
        encoding="utf-8",
    )
    (project_root / ".gitignore").write_text(_GITIGNORE, encoding="utf-8")

    # Source files
    (src / "__init__.py").write_text(_init_py(module), encoding="utf-8")
    (tools_dir / "__init__.py").write_text(_tools_init(), encoding="utf-8")

    # Skill file — use research skill if RAG is enabled
    if wiz.enable_rag:
        (skills_dir / "research.SKILL.md").write_text(_SKILL_RESEARCH, encoding="utf-8")
    else:
        (skills_dir / "example.SKILL.md").write_text(_SKILL_EXAMPLE, encoding="utf-8")

    # Workspace files — content depends on enabled features
    agent_display = wiz.agent_name or display_name
    (ws / "IDENTITY.md").write_text(_build_identity(agent_display, wiz), encoding="utf-8")
    (ws / "SOUL.md").write_text(_build_soul(wiz), encoding="utf-8")
    (ws / "USER.md").write_text(_build_user(wiz), encoding="utf-8")
    (ws / "TOOLS.md").write_text(_build_tools_doc(wiz), encoding="utf-8")
    (ws / "AGENTS.md").write_text(_build_agents_doc(wiz), encoding="utf-8")

    # .env with secrets (not committed — in .gitignore)
    env_lines = _build_env(wiz, module)
    if env_lines:
        (project_root / ".env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    # .env.example (safe to commit — no secrets)
    env_example_lines = _build_env_example(wiz, module)
    (project_root / ".env.example").write_text(
        "\n".join(env_example_lines) + "\n", encoding="utf-8"
    )

    # Tests
    (tests / "__init__.py").write_text("", encoding="utf-8")

    return project_root


# ---------------------------------------------------------------------------
# Content builders — generate workspace content based on wizard answers
# ---------------------------------------------------------------------------


def _build_identity(display_name: str, wiz: WizardConfig) -> str:
    lines = [
        "# Identity",
        "",
        f"- **Name**: {display_name}",
    ]
    if wiz.agent_role:
        lines.append(f"- **Role**: {wiz.agent_role}")
    lines.append(f"- **Language**: {wiz.language}")
    lines.append("- **Version**: 0.1.0")
    return "\n".join(lines) + "\n"


def _build_soul(wiz: WizardConfig) -> str:
    if wiz.personality:
        return f"# Personality\n\n{wiz.personality}\n"
    # Use richer personality if any features are enabled
    if wiz.enable_memory or wiz.enable_rag or wiz.enable_telegram:
        soul = _SOUL_RICH
        if wiz.enable_rag:
            soul += (
                "- Search the knowledge base before answering "
                "domain-specific questions\n"
            )
        return soul
    return _SOUL_PLACEHOLDER


def _build_user(wiz: WizardConfig) -> str:
    if wiz.enable_memory or wiz.enable_rag or wiz.enable_telegram:
        lines = [
            "# User Profile",
            "",
            "## Preferences",
            "- Appreciates clear, structured answers",
            "- Prefers concise responses with option to ask for more detail",
        ]
        if wiz.enable_memory:
            lines.append(
                "- Expects the agent to remember context across sessions"
            )
        if wiz.enable_rag:
            lines.append(
                "- Expects answers grounded in the knowledge base when available"
            )
        if wiz.enable_telegram:
            lines.append("- May interact via Telegram or CLI")
        return "\n".join(lines) + "\n"
    return _USER_PLACEHOLDER


def _build_tools_doc(wiz: WizardConfig) -> str:
    lines = [
        "# Available Tools",
        "",
        "## System Tools",
        "- `read_file` — Read files from the filesystem",
        "- `write_file` — Write or create files",
        "- `list_files` — List directory contents",
        "- `run_shell` — Execute shell commands",
    ]
    if wiz.enable_memory:
        lines += [
            "",
            "## Memory Tools",
            "- `remember_fact` — Store a fact about the user or conversation for later",
            "- `recall_facts` — Search your memory for relevant facts",
            "- `forget_fact` — Remove a stored fact",
            "",
            "Use memory tools proactively: remember user preferences, names, "
            "and context so you can provide a personalized experience.",
        ]
    if wiz.enable_rag:
        lines += [
            "",
            "## Knowledge Base (RAG)",
            "- `search_knowledge` — Search uploaded documents and reference materials",
            "- `add_to_knowledge` — Add new content to the knowledge base",
            "",
            "Use `search_knowledge` before answering domain-specific questions.",
        ]
    return "\n".join(lines) + "\n"


def _build_agents_doc(wiz: WizardConfig) -> str:
    lines = [
        "# Agent Configuration",
        "",
        "## Primary Agent",
        f"- **Provider**: {wiz.provider}",
    ]
    if wiz.model:
        lines.append(f"- **Model**: {wiz.model}")
    if wiz.ollama_base_url:
        lines.append(f"- **Base URL**: {wiz.ollama_base_url}")
    lines.append("- **Temperature**: 0.7")
    return "\n".join(lines) + "\n"


def _build_env(wiz: WizardConfig, module: str) -> list[str]:
    """Build .env content with actual secrets and runtime config. Not committed."""
    lines: list[str] = ["# Environment variables — DO NOT COMMIT this file", ""]
    has_content = False

    # Runtime model config — so `mr-lang chat/telegram --plugin X` uses the right model
    if wiz.provider:
        lines.append(f"MR_LANG_DEFAULT_PROVIDER={wiz.provider}")
        has_content = True
    if wiz.model:
        lines.append(f"MR_LANG_DEFAULT_MODEL={wiz.model}")
        has_content = True
    if has_content:
        lines.append("")

    if wiz.enable_memory:
        lines.append("MR_LANG_MEMORY_BACKEND=sqlite")
        has_content = True
        lines.append("")

    if wiz.enable_telegram and wiz.telegram and wiz.telegram.bot_token:
        lines.append(f"{module.upper()}_TELEGRAM_TOKEN={wiz.telegram.bot_token}")
        has_content = True

    if wiz.provider == "ollama" and wiz.ollama_base_url:
        lines.append(f"OLLAMA_BASE_URL={wiz.ollama_base_url}")
        has_content = True

    return lines if has_content else []


def _build_env_example(wiz: WizardConfig, module: str) -> list[str]:
    """Build .env.example content — safe to commit, no secrets."""
    lines = ["# Environment variables for this plugin", "# Copy to .env and fill in values", ""]

    # Model config
    lines.append(f"# MR_LANG_DEFAULT_PROVIDER={wiz.provider or 'ollama'}")
    if wiz.model:
        lines.append(f"# MR_LANG_DEFAULT_MODEL={wiz.model}")
    else:
        lines.append("# MR_LANG_DEFAULT_MODEL=llama3")
    lines.append("")

    if wiz.enable_memory:
        lines.append("# Memory backend: memory (in-process, lost on restart), sqlite, postgres")
        lines.append("MR_LANG_MEMORY_BACKEND=sqlite")
        lines.append("")

    if wiz.enable_telegram:
        lines.append(f"{module.upper()}_TELEGRAM_TOKEN=")

    if wiz.provider == "ollama":
        if wiz.ollama_base_url:
            lines.append(f"OLLAMA_BASE_URL={wiz.ollama_base_url}")
        else:
            lines.append("# OLLAMA_BASE_URL=http://127.0.0.1:11434")
    elif wiz.provider == "openai":
        lines.append("OPENAI_API_KEY=")
    elif wiz.provider == "anthropic":
        lines.append("ANTHROPIC_API_KEY=")

    return lines
