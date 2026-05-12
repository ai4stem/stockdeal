"""Claude wrapper with tiered model routing.

Tiers:
  fast  -> Haiku 4.5   (bulk: news classify, summarize)
  smart -> Sonnet 4.6  (fundamentals, disclosure, retrospective)
  deep  -> Opus 4.7    (final trade decisions, weekly review)

Conventions:
- Always pass a system prompt; cache it via cache_control for repeat-heavy
  workflows (per-ticker profile injection, lessons_learned RAG).
- All outputs that drive automation must return JSON (use response schema or
  strict instructions); narratives kept separately as 'rationale'.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from anthropic import Anthropic

from stockdeal.config import get_settings


class Tier(str, Enum):
    FAST = "fast"
    SMART = "smart"
    DEEP = "deep"


class ClaudeClient:
    def __init__(self) -> None:
        s = get_settings()
        self._client = Anthropic(api_key=s.anthropic_api_key.get_secret_value())
        self._models = {
            Tier.FAST: s.claude_model_fast,
            Tier.SMART: s.claude_model_smart,
            Tier.DEEP: s.claude_model_deep,
        }

    def ask(
        self,
        tier: Tier,
        system: str | list[dict[str, Any]],
        user: str | list[dict[str, Any]],
        max_tokens: int = 4096,
        cache_system: bool = True,
    ) -> Any:
        # TODO: full implementation with prompt caching for the system block,
        # JSON-mode handling, and usage logging.
        model = self._models[tier]
        if isinstance(system, str) and cache_system:
            system_block: list[dict[str, Any]] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]
        elif isinstance(system, str):
            system_block = [{"type": "text", "text": system}]
        else:
            system_block = system
        messages = (
            [{"role": "user", "content": user}]
            if isinstance(user, str)
            else [{"role": "user", "content": user}]
        )
        return self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_block,
            messages=messages,
        )
