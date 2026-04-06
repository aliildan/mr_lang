"""Tests for LoggingMiddleware."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from mr_lang.core.state import AgentState
from mr_lang.middleware.logging_mw import LoggingMiddleware


@pytest.fixture
def middleware() -> LoggingMiddleware:
    return LoggingMiddleware()


@pytest.fixture
def sample_state() -> AgentState:
    return {
        "messages": [HumanMessage(content="hello")],
        "workspace": {},
        "active_skills": [],
        "metadata": {},
    }


@pytest.mark.asyncio
async def test_before_model_returns_state(
    middleware: LoggingMiddleware, sample_state: AgentState
) -> None:
    """before_model should return the state unchanged."""
    result = await middleware.before_model(sample_state)
    assert result is sample_state


@pytest.mark.asyncio
async def test_after_model_returns_response(
    middleware: LoggingMiddleware, sample_state: AgentState
) -> None:
    """after_model should return the response unchanged."""
    response = AIMessage(content="hi there")
    result = await middleware.after_model(sample_state, response)
    assert result is response


@pytest.mark.asyncio
async def test_after_model_logs_tool_calls(
    middleware: LoggingMiddleware, sample_state: AgentState, capsys: pytest.CaptureFixture[str]
) -> None:
    """after_model should handle responses with tool calls."""
    # Set the start time so elapsed can be computed
    await middleware.before_model(sample_state)

    response = AIMessage(
        content="",
        tool_calls=[{"name": "read_file", "args": {"path": "x"}, "id": "1"}],
    )
    result = await middleware.after_model(sample_state, response)
    assert result is response


@pytest.mark.asyncio
async def test_timing_is_recorded(middleware: LoggingMiddleware, sample_state: AgentState) -> None:
    """The middleware should record a start time in before_model."""
    assert middleware._call_start == 0.0
    await middleware.before_model(sample_state)
    assert middleware._call_start > 0.0


@pytest.mark.asyncio
async def test_middleware_handles_empty_messages() -> None:
    """Middleware should work with an empty messages list."""
    mw = LoggingMiddleware()
    state: AgentState = {
        "messages": [],
        "workspace": {},
        "active_skills": [],
        "metadata": {},
    }
    result = await mw.before_model(state)
    assert result is state


# ---------------------------------------------------------------------------
# Verbose mode — before_tool / after_tool output
# ---------------------------------------------------------------------------


class TestVerboseLogging:
    """Verify that verbose=True/False controls tool-level stderr output."""

    @pytest.mark.asyncio
    async def test_non_verbose_before_tool_produces_no_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With verbose=False, before_tool writes nothing to stderr."""
        mw = LoggingMiddleware(verbose=False)
        await mw.before_tool("search", {"q": "x"})
        captured = capsys.readouterr()
        assert captured.err == ""

    @pytest.mark.asyncio
    async def test_verbose_before_tool_writes_tool_name_to_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With verbose=True, before_tool writes the tool name to stderr."""
        mw = LoggingMiddleware(verbose=True)
        await mw.before_tool("search", {"q": "x"})
        captured = capsys.readouterr()
        assert "search" in captured.err

    @pytest.mark.asyncio
    async def test_verbose_after_tool_writes_result_to_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With verbose=True, after_tool writes the result preview to stderr."""
        mw = LoggingMiddleware(verbose=True)
        await mw.after_tool("search", {}, "result text")
        captured = capsys.readouterr()
        assert "result text" in captured.err

    @pytest.mark.asyncio
    async def test_verbose_after_tool_none_result_produces_no_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With verbose=True, after_tool skips output when result is None."""
        mw = LoggingMiddleware(verbose=True)
        await mw.after_tool("search", {}, None)
        captured = capsys.readouterr()
        assert captured.err == ""

    @pytest.mark.asyncio
    async def test_verbose_after_tool_long_result_contains_truncation_marker(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With verbose=True, results longer than 200 chars show a (+N chars) marker."""
        from mr_lang.middleware.logging_mw import _RESULT_PREVIEW_LEN

        mw = LoggingMiddleware(verbose=True)
        long_result = "z" * (_RESULT_PREVIEW_LEN + 50)
        await mw.after_tool("search", {}, long_result)
        captured = capsys.readouterr()
        assert "(+" in captured.err
        assert "chars)" in captured.err
