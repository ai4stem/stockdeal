"""Claude wrapper with tiered model routing.

Tiers:
  fast  -> Haiku 4.5   (bulk: news classify, summarize)
  smart -> Sonnet 4.6  (fundamentals, disclosure, retrospective)
  deep  -> Opus 4.7    (final trade decisions, weekly review)

Conventions:
- The `system` argument is always wrapped as a single text block with
  prompt-caching enabled (cache_control=ephemeral) when `cache_system=True`,
  so repeat-heavy workflows (per-ticker profile, lessons RAG) hit the cache.
- JSON mode: pass `json_mode=True`; we append a strict-format reminder to the
  system block and parse the first JSON object found. The raw text is always
  preserved on the result.
- Retries: rate limits (429) and 5xx are retried with exponential backoff
  via tenacity. Network errors get the same treatment.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from stockdeal.config import get_settings
from stockdeal.logging import get_logger

log = get_logger(__name__)


class Tier(str, Enum):
    FAST = "fast"
    SMART = "smart"
    DEEP = "deep"


_JSON_INSTRUCTION = (
    "\n\n응답은 반드시 단일 JSON 객체로만 출력하세요. "
    "마크다운 코드 블록이나 설명 텍스트 없이 JSON만 응답해야 합니다."
)
_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class LLMResult:
    text: str
    parsed: Any | None
    model: str
    tier: Tier
    stop_reason: str | None
    usage: dict[str, int] = field(default_factory=dict)

    @property
    def cache_hit_ratio(self) -> float:
        read = self.usage.get("cache_read_input_tokens", 0)
        total_input = self.usage.get("input_tokens", 0) + read
        return read / total_input if total_input else 0.0


def _retryable_exceptions() -> tuple[type[BaseException], ...]:
    return (
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
        anthropic.APITimeoutError,
        anthropic.InternalServerError,
    )


class ClaudeClient:
    def __init__(self) -> None:
        s = get_settings()
        self._client = anthropic.Anthropic(api_key=s.anthropic_api_key.get_secret_value())
        self._models: dict[Tier, str] = {
            Tier.FAST: s.claude_model_fast,
            Tier.SMART: s.claude_model_smart,
            Tier.DEEP: s.claude_model_deep,
        }

    def ask(
        self,
        tier: Tier | str,
        system: str,
        user: str,
        max_tokens: int = 4096,
        json_mode: bool = False,
        cache_system: bool = True,
        temperature: float = 0.2,
        max_retries: int = 4,
    ) -> LLMResult:
        tier = Tier(tier) if isinstance(tier, str) else tier
        model = self._models[tier]
        if json_mode:
            system = system + _JSON_INSTRUCTION

        system_block: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": system,
                **({"cache_control": {"type": "ephemeral"}} if cache_system else {}),
            }
        ]
        messages = [{"role": "user", "content": user}]

        @retry(
            reraise=True,
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1.5, min=1, max=20),
            retry=retry_if_exception_type(_retryable_exceptions()),
        )
        def _call() -> Any:
            return self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_block,
                messages=messages,
                temperature=temperature,
            )

        response = _call()

        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", 0),
            "output_tokens": getattr(response.usage, "output_tokens", 0),
            "cache_creation_input_tokens": getattr(
                response.usage, "cache_creation_input_tokens", 0
            ),
            "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0),
        }
        parsed = _try_parse_json(text) if json_mode else None

        log.info(
            "claude_ask",
            tier=tier.value,
            model=model,
            stop=response.stop_reason,
            json_mode=json_mode,
            **usage,
        )
        return LLMResult(
            text=text,
            parsed=parsed,
            model=model,
            tier=tier,
            stop_reason=response.stop_reason,
            usage=usage,
        )


def _try_parse_json(text: str) -> Any | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_PATTERN.search(text)
        if not match:
            log.warning("claude_json_unparseable", preview=text[:200])
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            log.warning("claude_json_unparseable_after_extract", preview=text[:200])
            return None
