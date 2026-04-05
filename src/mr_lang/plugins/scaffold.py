"""Scaffold new plugin projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mr_lang.exceptions import PluginError

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_SOUL_DEFAULT = """\
# Personality

Be helpful, clear, and concise.
"""

_USER_DEFAULT = """\
# User Profile

Adapt to the user's needs and preferences.
"""

_TOOLS_DOC_DEFAULT = """\
# Tools

This document describes the tools available to the agent.
"""

_AGENTS_DOC_DEFAULT = """\
# Agents

Describe sub-agents or collaboration patterns here.
"""

_EXAMPLE_SKILL = """\
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
) -> str:
    deps = extra_deps or []
    deps_str = ", ".join(f'"{d}"' for d in deps)
    servers = mcp_servers or []
    servers_str = ", ".join(f'"{s}"' for s in servers)
    return f"""\
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
    return '''\
"""Custom tools for this plugin.

Define LangChain @tool functions here. They will be auto-discovered
when the plugin is activated. Example:

    from langchain_core.tools import tool

    @tool
    def my_tool(query: str) -> str:
        \"""Describe what this tool does — this is visible to the LLM.\"""
        return f"Result for {query}"

No tools defined yet — this is fine, you'll just see a warning until you add some.
"""

from __future__ import annotations
'''


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

TEMPLATES = {"basic", "telegram-bot", "teaching-assistant"}


def _extra_deps(template: str) -> list[str]:
    if template == "telegram-bot":
        return ["python-telegram-bot>=21"]
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class WizardConfig:
    """All parameters the wizard can collect."""

    name: str = ""
    template: str = "basic"
    description: str = ""
    author: str = ""
    agent_name: str = ""
    agent_role: str = ""
    personality: str = ""
    language: str = "English"
    provider: str = "ollama"
    model: str = "llama3"
    mcp_servers: list[str] = field(default_factory=list)
    enable_telegram: bool = False


def scaffold_project(
    name: str,
    path: Path | None = None,
    template: str = "basic",
    description: str = "",
    wizard: WizardConfig | None = None,
) -> Path:
    """Create a new plugin project directory structure.

    Args:
        name: Plugin name (kebab-case, e.g. 'herr-molly').
        path: Parent directory in which to create the project. Defaults to cwd.
        template: One of 'basic', 'telegram-bot', 'teaching-assistant'.
        description: Short project description.
        wizard: Optional wizard config with additional parameters.

    Returns:
        Path to the created project root.
    """
    if template not in TEMPLATES:
        raise PluginError(
            f"Unknown template '{template}'. Choose from: {', '.join(sorted(TEMPLATES))}"
        )

    base = (path or Path.cwd()).resolve()
    project_root = base / name
    if project_root.exists():
        raise PluginError(f"Directory already exists: {project_root}")

    module = name.replace("-", "_")
    display_name = name.replace("-", " ").title()
    desc = description or f"A mr_lang plugin: {display_name}"
    wiz = wizard or WizardConfig()

    # Merge template with wizard overrides
    if wiz.enable_telegram and template != "telegram-bot":
        template = "telegram-bot"

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
            extra_deps=_extra_deps(template),
            mcp_servers=wiz.mcp_servers,
        ),
        encoding="utf-8",
    )
    (project_root / "pyproject.toml").write_text(
        _pyproject_toml(name, module, desc),
        encoding="utf-8",
    )

    # Source files
    (src / "__init__.py").write_text(_init_py(module), encoding="utf-8")
    (tools_dir / "__init__.py").write_text(_tools_init(), encoding="utf-8")
    (skills_dir / "example.SKILL.md").write_text(_EXAMPLE_SKILL, encoding="utf-8")

    # Workspace files — use wizard values if provided, else defaults
    agent_display = wiz.agent_name or display_name
    identity = _build_identity(template, agent_display, wiz)
    (ws / "IDENTITY.md").write_text(identity, encoding="utf-8")

    soul = _build_soul(wiz)
    (ws / "SOUL.md").write_text(soul, encoding="utf-8")
    (ws / "USER.md").write_text(_USER_DEFAULT, encoding="utf-8")
    (ws / "TOOLS.md").write_text(_TOOLS_DOC_DEFAULT, encoding="utf-8")

    agents_doc = _build_agents_doc(wiz)
    (ws / "AGENTS.md").write_text(agents_doc, encoding="utf-8")

    # .env.example for easy onboarding
    env_lines = ["# Environment variables for this plugin", ""]
    if wiz.enable_telegram or template == "telegram-bot":
        env_lines.append("MR_LANG_TELEGRAM_BOT_TOKEN=")
    if wiz.provider == "openai":
        env_lines.append("OPENAI_API_KEY=")
    elif wiz.provider == "anthropic":
        env_lines.append("ANTHROPIC_API_KEY=")
    env_lines.append("")
    (project_root / ".env.example").write_text("\n".join(env_lines), encoding="utf-8")

    # Tests
    (tests / "__init__.py").write_text("", encoding="utf-8")

    return project_root


# ---------------------------------------------------------------------------
# Wizard-aware content builders
# ---------------------------------------------------------------------------


def _build_identity(template: str, display_name: str, wiz: WizardConfig) -> str:
    role = wiz.agent_role or {
        "basic": "AI Assistant",
        "telegram-bot": "Telegram Bot Assistant",
        "teaching-assistant": "Teaching Assistant",
    }.get(template, "AI Assistant")

    lines = [
        "# Identity",
        "",
        f"- **Name**: {display_name}",
        f"- **Role**: {role}",
        f"- **Language**: {wiz.language}",
        "- **Version**: 0.1.0",
    ]
    if template == "telegram-bot":
        lines.append("- **Platform**: Telegram")
    if template == "teaching-assistant":
        lines.append("- **Specialization**: Education")
    return "\n".join(lines) + "\n"


def _build_soul(wiz: WizardConfig) -> str:
    if wiz.personality:
        return f"# Personality\n\n{wiz.personality}\n"
    return _SOUL_DEFAULT


def _build_agents_doc(wiz: WizardConfig) -> str:
    lines = [
        "# Agent Configuration",
        "",
        "## Primary Agent",
        f"- **Provider**: {wiz.provider}",
        f"- **Model**: {wiz.model}",
        "- **Temperature**: 0.7",
    ]
    return "\n".join(lines) + "\n"
