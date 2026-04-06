"""Tests for memory tools (remember, recall, forget)."""

from __future__ import annotations

import pytest
from langgraph.store.memory import InMemoryStore

from mr_lang.tools.builtin.memory import create_memory_tools


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def tools(store: InMemoryStore):
    return create_memory_tools(store, namespace_prefix=("test-plugin",))


def _get_tool(tools, name: str):
    return next(t for t in tools if t.name == name)


class TestMemoryTools:
    def test_creates_three_tools(self, tools):
        assert len(tools) == 3
        names = {t.name for t in tools}
        assert names == {"remember_fact", "recall_facts", "forget_fact"}

    @pytest.mark.asyncio
    async def test_remember_and_recall(self, tools, store):
        remember = _get_tool(tools, "remember_fact")
        recall = _get_tool(tools, "recall_facts")

        result = await remember.ainvoke({"key": "user_name", "fact": "Ali"})
        assert "Remembered" in result

        result = await recall.ainvoke({"query": "name"})
        assert "Ali" in result

    @pytest.mark.asyncio
    async def test_forget(self, tools, store):
        remember = _get_tool(tools, "remember_fact")
        forget = _get_tool(tools, "forget_fact")
        recall = _get_tool(tools, "recall_facts")

        await remember.ainvoke({"key": "temp", "fact": "temporary data"})
        result = await forget.ainvoke({"key": "temp"})
        assert "Forgot" in result

        result = await recall.ainvoke({"query": "temporary"})
        assert "No relevant facts" in result

    @pytest.mark.asyncio
    async def test_recall_empty(self, tools):
        recall = _get_tool(tools, "recall_facts")
        result = await recall.ainvoke({"query": "anything"})
        assert "No relevant facts" in result

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, store):
        tools_a = create_memory_tools(store, namespace_prefix=("plugin-a",))
        tools_b = create_memory_tools(store, namespace_prefix=("plugin-b",))

        remember_a = _get_tool(tools_a, "remember_fact")
        recall_b = _get_tool(tools_b, "recall_facts")

        await remember_a.ainvoke({"key": "secret", "fact": "plugin A secret"})

        result = await recall_b.ainvoke({"query": "secret"})
        assert "No relevant facts" in result
