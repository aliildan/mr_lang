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
async def test_timing_is_recorded(
    middleware: LoggingMiddleware, sample_state: AgentState
) -> None:
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
