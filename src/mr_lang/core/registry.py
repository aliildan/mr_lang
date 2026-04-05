"""Tool and skill registries."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from mr_lang.exceptions import SkillError, ToolError
from mr_lang.skills.schema import SkillDefinition


class ToolRegistry:
    """Singleton registry for all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ToolError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise ToolError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def list(self) -> list[BaseTool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)


class SkillRegistry:
    """Singleton registry for all available skills."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        if skill.name in self._skills:
            raise SkillError(f"Skill '{skill.name}' is already registered")
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition:
        if name not in self._skills:
            raise SkillError(f"Skill '{name}' not found in registry")
        return self._skills[name]

    def list(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def names(self) -> list[str]:
        return list(self._skills.keys())

    def __len__(self) -> int:
        return len(self._skills)
