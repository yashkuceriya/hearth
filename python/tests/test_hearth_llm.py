"""Tests for the shared Claude LLM client.

We avoid hitting the real API by:
- Testing the "no API key" path directly (available=False).
- Injecting a fake `_client` into `LLMClient` to exercise call + parse.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from hearth_llm import LLMClient, LLMResult


def test_client_unavailable_without_api_key():
    with patch.dict("os.environ", {}, clear=True):
        client = LLMClient()
        assert client.available is False


def test_client_unavailable_with_empty_key():
    client = LLMClient(api_key="")
    assert client.available is False


def test_call_raises_when_unavailable():
    client = LLMClient(api_key=None)
    try:
        client.call(system="s", user="u")
    except RuntimeError as e:
        assert "not available" in str(e)
        return
    raise AssertionError("expected RuntimeError")


def test_parse_text_response():
    fake_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="hello world")],
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=20,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
        stop_reason="end_turn",
    )
    result = LLMClient._parse(fake_response)
    assert isinstance(result, LLMResult)
    assert result.text == "hello world"
    assert result.input_tokens == 100
    assert result.output_tokens == 20
    assert result.cache_hit is False
    assert result.stop_reason == "end_turn"


def test_parse_tool_use_response():
    fake_response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="Let me check."),
            SimpleNamespace(
                type="tool_use",
                id="tu_123",
                name="lookup_valuation",
                input={"address": "123 Main St"},
            ),
        ],
        usage=SimpleNamespace(
            input_tokens=150,
            output_tokens=30,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=120,
        ),
        stop_reason="tool_use",
    )
    result = LLMClient._parse(fake_response)
    assert result.text == "Let me check."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "lookup_valuation"
    assert result.tool_calls[0]["input"]["address"] == "123 Main St"
    assert result.cache_hit is True
    assert result.cache_read_tokens == 120


def test_parse_json_strips_fences():
    client = LLMClient(api_key=None)
    assert client.parse_json('{"a": 1}') == {"a": 1}
    assert client.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert client.parse_json("```\n{\"a\": 1}\n```") == {"a": 1}


def test_parse_json_returns_empty_on_failure():
    client = LLMClient(api_key=None)
    assert client.parse_json("not json at all") == {}
