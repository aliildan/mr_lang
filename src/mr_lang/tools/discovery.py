"""Auto-discover tools from entry points and directories."""

from __future__ import annotations

import importlib
import sys
from importlib.metadata import entry_points

from langchain_core.tools import BaseTool

from mr_lang.core.registry import ToolRegistry


def discover_tools_from_entry_points(
    registry: ToolRegistry,
    group: str = "mr_lang.tools",
) -> None:
    """Load tools registered via setuptools entry points.

    Each entry point should point to a module containing BaseTool instances
    as module-level attributes.
    """
    if sys.version_info >= (3, 12):
        eps = entry_points(group=group)
    else:
        eps = entry_points().get(group, [])

    for ep in eps:
        module = ep.load()
        names = module.__all__ if hasattr(module, "__all__") else dir(module)

        for name in names:
            obj = getattr(module, name, None)
            if isinstance(obj, BaseTool):
                registry.register(obj)


def discover_tools_from_module(
    registry: ToolRegistry,
    module_path: str,
) -> None:
    """Load tools from a Python module path (e.g., 'my_package.tools').

    Imports the module and registers any BaseTool instances found.
    """
    module = importlib.import_module(module_path)
    for name in dir(module):
        obj = getattr(module, name, None)
        if isinstance(obj, BaseTool):
            registry.register(obj)
