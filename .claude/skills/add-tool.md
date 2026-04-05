---
name: add-tool
description: Scaffold a new LangChain tool module with test file for the mr_lang framework
---

# Add Tool

Create a new tool for the mr_lang framework. Tools are Python functions decorated with `@tool` from langchain_core.

## Instructions

When the user asks to add a new tool, follow these steps:

1. Ask for the tool name (snake_case) and a brief description if not provided
2. Create the tool module at `src/mr_lang/tools/<name>.py`
3. Create a test file at `tests/tools/test_<name>.py`

## Tool Template

```python
"""<Tool description>."""

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

## Rules

- Tool name MUST be snake_case
- ALL parameters MUST have type hints
- Docstring is REQUIRED — it becomes the tool description visible to the LLM
- Do NOT use `config` or `runtime` as parameter names (reserved by LangChain)
- If the tool needs access to runtime state/store/context, use `ToolRuntime` parameter:
  ```python
  from mr_lang.core.state import ToolRuntime

  @tool
  def my_tool(query: str, runtime: ToolRuntime) -> str:
      """..."""
      store = runtime.store
  ```
- Return type should be `str` for simple tools, or a dict/Pydantic model for structured data
- Add the tool to the registry in `src/mr_lang/tools/__init__.py`

## Test Template

```python
"""Tests for <tool_name> tool."""

import pytest
from mr_lang.tools.<module> import <tool_name>


def test_<tool_name>_basic():
    result = <tool_name>.invoke({"<param>": "<value>"})
    assert result is not None


def test_<tool_name>_edge_case():
    # Test edge cases
    pass
```
