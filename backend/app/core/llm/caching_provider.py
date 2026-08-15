"""Caching decorator around any :class:`LLMProvider` (design §4.1, §6.8).

Every call first checks Redis; a hit is returned with zero cost and is marked
``from_cache=True`` so callers can log a zero-cost trace step. A miss calls
through to the wrapped provider and stores the result.
"""

from __future__ import annotations

from app.core.llm.cache import LLMResponseCache, build_cache_key
from app.core.llm.provider import LLMProvider, LLMResponse, Message, ModelTier
from app.core.logging import get_logger

logger = get_logger(__name__)


class CachingLLMProvider:
    """Wraps a concrete provider with the Redis LLM cache."""

    def __init__(self, inner: LLMProvider, cache: LLMResponseCache) -> None:
        self._inner = inner
        self._cache = cache

    async def complete(
        self,
        messages: list[Message],
        model_tier: ModelTier,
        max_tokens: int,
        tools: list[dict[str, object]] | None = None,
    ) -> LLMResponse:
        # Tool-bearing calls are not cached: their results depend on runtime
        # tool availability/state, so caching would risk serving stale or
        # incorrect tool-call plans.
        if tools:
            return await self._inner.complete(messages, model_tier, max_tokens, tools)

        key = build_cache_key(messages, model_tier)
        cached = await self._cache.get(key)
        if cached is not None:
            logger.info("llm.cache.hit", extra={"event": "llm.cache.hit"})
            return cached

        response = await self._inner.complete(messages, model_tier, max_tokens, tools)
        await self._cache.set(key, response)
        return response
