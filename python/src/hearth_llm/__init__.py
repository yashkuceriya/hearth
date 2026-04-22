"""Shared Claude API client for Hearth agents.

Exposes `LLMClient` with prompt caching and a `StructuredAgentCall` helper
that returns `LLMResult` objects with parsed content, reasoning, and tool calls.
Falls back to a no-op client when ANTHROPIC_API_KEY is unset (dev/test).
"""

from hearth_llm.client import LLMClient, LLMResult, get_default_client

__all__ = ["LLMClient", "LLMResult", "get_default_client"]
