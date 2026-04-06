---
name: add-tool
description: Scaffold a new LangChain tool module with test file for the mr_lang framework
---

# Add Tool

Create a new tool for the mr_lang framework. Tools are Python functions decorated with `@tool` from langchain_core.

## Instructions

When the user asks to add a new tool, follow these steps:

1. Ask for the tool name (snake_case) and a brief description if not provided
2. Create the tool module at `src/mr_lang/tools/builtin/<name>.py`
3. Create a test file at `tests/tools/test_<name>.py`
4. Register the tool in `src/mr_lang/cli/setup.py` (add to the builtin tools list)

## Tool Template

```python
"""<Tool description>."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def <tool_name>(<params>) -> <return_type>:
    """<Description of what this tool does — this becomes the LLM-visible description>.

    Args:
        <param>: <description>
    """
    # Implementation here
    pass
```

For async tools:

```python
@tool
async def <tool_name>(<params>) -> <return_type>:
    """<Description>."""
    pass
```

## Rules

- Tool name MUST be snake_case
- ALL parameters MUST have type hints
- Docstring is REQUIRED — it becomes the tool description visible to the LLM
- Do NOT use `config` or `runtime` as parameter names (reserved by LangChain)
- Return type should be `str` for simple tools
- Builtin tools go in `src/mr_lang/tools/builtin/`
- Plugin-specific tools go in the plugin's `tools_module` path
- Tools that need a store/namespace (like memory tools) should use a factory function:
  ```python
  def create_my_tools(store: BaseStore) -> list[BaseTool]:
      @tool
      async def my_tool(query: str) -> str:
          """..."""
          result = await store.asearch(...)
          return str(result)
      return [my_tool]
  ```

## Test Template

```python
"""Tests for <tool_name> tool."""

from __future__ import annotations

import pytest

from mr_lang.tools.builtin.<module> import <tool_name>


class TestToolName:
    def test_basic(self):
        result = <tool_name>.invoke({"<param>": "<value>"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_async(self):
        result = await <tool_name>.ainvoke({"<param>": "<value>"})
        assert result is not None
```

## Registration

After creating the tool, register it in `src/mr_lang/cli/setup.py`:

```python
from mr_lang.tools.builtin.<module> import <tool_name>

# In setup_agent(), add to the builtin tools list:
for t in [read_file, write_file, list_files, run_shell, <tool_name>]:
    registry.register(t)
```
