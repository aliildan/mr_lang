"""Tests for MCP client helpers — _build_args_schema and _extract_text."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mr_lang.adapters.mcp.client import _MAX_TOOL_RESULT_CHARS, _build_args_schema, _extract_text


# ---------------------------------------------------------------------------
# _build_args_schema
# ---------------------------------------------------------------------------


def test_empty_schema_produces_no_required_fields() -> None:
    """An empty schema yields a model that can be instantiated with no args."""
    Model = _build_args_schema({})
    instance = Model()
    assert instance is not None


def test_empty_schema_fields_are_empty() -> None:
    """An empty schema produces a model with no fields."""
    Model = _build_args_schema({})
    assert Model.model_fields == {}


def test_required_string_field_present() -> None:
    """Schema with one required string field creates a model with that field."""
    schema = {
        "properties": {"url": {"type": "string", "description": "Target URL"}},
        "required": ["url"],
    }
    Model = _build_args_schema(schema)
    assert "url" in Model.model_fields


def test_required_string_field_accepts_value() -> None:
    """Required string field can be set to a string value."""
    schema = {
        "properties": {"url": {"type": "string", "description": "Target URL"}},
        "required": ["url"],
    }
    Model = _build_args_schema(schema)
    instance = Model(url="https://example.com")
    assert instance.url == "https://example.com"


def test_required_field_raises_without_value() -> None:
    """Instantiating without a required field raises ValidationError."""
    schema = {
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }
    Model = _build_args_schema(schema)
    with pytest.raises(ValidationError):
        Model()


def test_optional_integer_field_defaults_to_none() -> None:
    """An optional integer field defaults to None when not provided."""
    schema = {
        "properties": {"limit": {"type": "integer", "description": "Max items"}},
    }
    Model = _build_args_schema(schema)
    instance = Model()
    assert instance.limit is None


def test_optional_integer_field_accepts_int() -> None:
    """An optional integer field accepts an integer value."""
    schema = {
        "properties": {"limit": {"type": "integer"}},
    }
    Model = _build_args_schema(schema)
    instance = Model(limit=42)
    assert instance.limit == 42


def test_mixed_fields_required_is_set() -> None:
    """Mixed schema: required field must be provided."""
    schema = {
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["query"],
    }
    Model = _build_args_schema(schema)
    with pytest.raises(ValidationError):
        Model()


def test_mixed_fields_optional_defaults_none() -> None:
    """Mixed schema: optional field defaults to None when only required is given."""
    schema = {
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["query"],
    }
    Model = _build_args_schema(schema)
    instance = Model(query="hello")
    assert instance.query == "hello"
    assert instance.limit is None


def test_unknown_type_falls_back_to_str() -> None:
    """An unrecognised JSON type falls back to Python str."""
    schema = {
        "properties": {"data": {"type": "unknown"}},
        "required": ["data"],
    }
    Model = _build_args_schema(schema)
    instance = Model(data="anything")
    assert instance.data == "anything"


def test_unknown_type_field_annotation_is_str() -> None:
    """Field with unknown type is annotated as str (not None-able when required)."""
    schema = {
        "properties": {"data": {"type": "unknown"}},
        "required": ["data"],
    }
    Model = _build_args_schema(schema)
    # Required field with unknown type — should use str as annotation
    field_info = Model.model_fields["data"]
    # annotation will be `str` since it is required (no None union)
    assert field_info.annotation is str


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------


class _Item:
    """Minimal stand-in for an MCP content item that has a .text attribute."""

    def __init__(self, text: str) -> None:
        self.text = text

    def __str__(self) -> str:  # pragma: no cover — only used in fallback path
        return f"<Item:{self.text}>"


class _NoTextItem:
    """MCP content item without a .text attribute."""

    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value


def test_list_with_text_items_joins_newlines() -> None:
    """List of items with .text are joined with newlines."""
    items = [_Item("hello"), _Item("world")]
    result = _extract_text(items)
    assert result == "hello\nworld"


def test_list_with_no_text_falls_back_to_str() -> None:
    """Items without .text attribute use str() representation."""
    items = [_NoTextItem("fallback")]
    result = _extract_text(items)
    assert result == "fallback"


def test_list_mixed_text_and_no_text() -> None:
    """Mixed list: .text items and str-fallback items are concatenated."""
    items = [_Item("first"), _NoTextItem("second")]
    result = _extract_text(items)
    assert result == "first\nsecond"


def test_plain_string_returned_as_is() -> None:
    """A plain string result is returned unchanged."""
    assert _extract_text("plain output") == "plain output"


def test_non_string_non_list_coerced_to_str() -> None:
    """Arbitrary objects are coerced via str()."""
    assert _extract_text(42) == "42"


def test_result_beyond_limit_is_truncated() -> None:
    """Results longer than _MAX_TOOL_RESULT_CHARS are truncated with a suffix."""
    long_result = "x" * (_MAX_TOOL_RESULT_CHARS + 100)
    output = _extract_text(long_result)
    assert len(output) > _MAX_TOOL_RESULT_CHARS  # suffix adds a bit
    assert "...[result truncated" in output
    assert f"{len(long_result)} chars total" in output


def test_result_at_limit_is_not_truncated() -> None:
    """Results exactly at the limit are returned without a truncation suffix."""
    exact_result = "y" * _MAX_TOOL_RESULT_CHARS
    output = _extract_text(exact_result)
    assert "truncated" not in output
    assert output == exact_result


def test_truncation_preserves_leading_chars() -> None:
    """Truncated output starts with the first _MAX_TOOL_RESULT_CHARS characters."""
    long_result = "a" * (_MAX_TOOL_RESULT_CHARS + 50)
    output = _extract_text(long_result)
    assert output.startswith("a" * _MAX_TOOL_RESULT_CHARS)
