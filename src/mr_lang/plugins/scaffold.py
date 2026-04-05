"""Scaffold new plugin projects."""

from __future__ import annotations

from pathlib import Path

from mr_lang.exceptions import PluginError

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_IDENTITY_BASIC = """\
# Identity

- Name: {display_name}
- Role: AI Assistant
- Version: 0.1.0
"""

_IDENTITY_TELEGRAM = """\
# Identity

- Name: {display_name}
- Role: Telegram Bot Assistant
- Version: 0.1.0
- Platform: Telegram
"""

_IDENTITY_TEACHING = """\
# Identity

- Name: {display_name}
- Role: Teaching Assistant
- Version: 0.1.0
- Specialization: Education
"""

_SOUL = """\
# Personality

Be helpful, clear, and concise.
"""

_USER = """\
# User Profile

Adapt to the user's needs and preferences.
"""

_TOOLS_DOC = """\
# Tools

This document describes the tools available to the agent.
"""

_AGENTS_DOC = """\
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
    extra_deps: list[str] | None = None,
) -> str:
    deps = extra_deps or []
    deps_str = ", ".join(f'"{d}"' for d in deps)
    return f"""\
[plugin]
name = "{name}"
version = "0.1.0"
description = "{description}"
author = ""

[plugin.paths]
workspace = "./workspace"
skills = "./src/{module}/skills"
tools_module = "{module}.tools"

[plugin.mcp]
servers = []

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


def _get_identity(template: str, display_name: str) -> str:
    templates = {
        "basic": _IDENTITY_BASIC,
        "telegram-bot": _IDENTITY_TELEGRAM,
        "teaching-assistant": _IDENTITY_TEACHING,
    }
    return templates.get(template, _IDENTITY_BASIC).format(display_name=display_name)


def _extra_deps(template: str) -> list[str]:
    if template == "telegram-bot":
        return ["python-telegram-bot>=21"]
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scaffold_project(
    name: str,
    path: Path | None = None,
    template: str = "basic",
    description: str = "",
) -> Path:
    """Create a new plugin project directory structure.

    Args:
        name: Plugin name (kebab-case, e.g. 'herr-molly').
        path: Parent directory in which to create the project. Defaults to cwd.
        template: One of 'basic', 'telegram-bot', 'teaching-assistant'.
        description: Short project description.

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
        _manifest_toml(name, module, desc, extra_deps=_extra_deps(template)),
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

    # Workspace files
    (ws / "IDENTITY.md").write_text(
        _get_identity(template, display_name), encoding="utf-8"
    )
    (ws / "SOUL.md").write_text(_SOUL, encoding="utf-8")
    (ws / "USER.md").write_text(_USER, encoding="utf-8")
    (ws / "TOOLS.md").write_text(_TOOLS_DOC, encoding="utf-8")
    (ws / "AGENTS.md").write_text(_AGENTS_DOC, encoding="utf-8")

    # Tests
    (tests / "__init__.py").write_text("", encoding="utf-8")

    return project_root
