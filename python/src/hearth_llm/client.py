"""Claude API client with prompt caching for Hearth agents.

Design:
- The system prompt + tool schema are marked `cache_control={"type": "ephemeral"}`
  so Anthropic caches them for the 5-minute TTL window. Per-user turns pay only
  the incremental tokens.
- `available` returns False when no API key is configured — callers fall back
  to deterministic rule-based reasoning. This keeps tests hermetic and dev
  environments cheap.
- Token + cost telemetry is emitted via structured log lines; wire to metrics
  separately (see issue #16).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TIMEOUT_S = 10.0


@dataclass
class LLMResult:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    stop_reason: str = ""

    @property
    def cache_hit(self) -> bool:
        return self.cache_read_tokens > 0


class LLMClient:
    """Thin wrapper over Anthropic's SDK with caching + graceful degradation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self._client = None
        if self.api_key:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self.api_key, timeout=timeout_s)
            except ImportError:
                logger.warning("anthropic SDK not installed; LLM disabled")
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def call(
        self,
        system: str,
        user: str,
        tools: Optional[list[dict[str, Any]]] = None,
        cached_system: bool = True,
    ) -> LLMResult:
        """Call the model with prompt caching on the system block.

        Raises if `self.available` is False — callers should check first.
        """
        if self._client is None:
            raise RuntimeError("LLMClient not available (no ANTHROPIC_API_KEY)")

        system_block: list[dict[str, Any]] = [{"type": "text", "text": system}]
        if cached_system:
            system_block[0]["cache_control"] = {"type": "ephemeral"}

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_block,
            "messages": [{"role": "user", "content": user}],
        }
        if tools:
            kwargs["tools"] = tools

        response = self._client.messages.create(**kwargs)
        return self._parse(response)

    @staticmethod
    def _parse(response: Any) -> LLMResult:
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in getattr(response, "content", []):
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(getattr(block, "text", ""))
            elif btype == "tool_use":
                tool_calls.append({
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": getattr(block, "input", {}),
                })
        usage = getattr(response, "usage", None)
        result = LLMResult(
            text="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) if usage else 0,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) if usage else 0,
            stop_reason=getattr(response, "stop_reason", "") or "",
        )
        logger.info(
            "llm_call tokens=in/%d/out/%d cache=create/%d/read/%d",
            result.input_tokens,
            result.output_tokens,
            result.cache_creation_tokens,
            result.cache_read_tokens,
        )
        return result

    def parse_json(self, text: str) -> dict[str, Any]:
        """Best-effort JSON extraction from a text block (strips fences)."""
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.lower().startswith("json"):
                stripped = stripped[4:]
            stripped = stripped.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return {}


_default: Optional[LLMClient] = None


def get_default_client() -> LLMClient:
    """Process-wide singleton so the 5-minute cache is shared across agents."""
    global _default
    if _default is None:
        _default = LLMClient()
    return _default
