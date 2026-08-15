"""Redis-backed LLM response cache (design §4.1, §6.8).

Cache keys include every input that changes the output — the prompt content,
``model_tier``, and the sorted set of relevant document ids — so a cache hit
is never returned for a differently-scoped question (design §6.8 rule).
"""

from __future__ import annotations

import hashlib
import json

from redis.asyncio import Redis

from app.core.llm.provider import LLMResponse, Message, ModelTier
from app.core.logging import get_logger

logger = get_logger(__name__)

_CACHE_PREFIX = "llm:"


def build_cache_key(
    messages: list[Message],
    model_tier: ModelTier,
    *,
    document_ids: list[str] | None = None,
) -> str:
    """``llm:{sha256(prompt + model_tier + sorted(doc_ids))}`` (design §6.8)."""
    payload = {
        "messages": [message.model_dump() for message in messages],
        "model_tier": model_tier,
        "document_ids": sorted(document_ids or []),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"{_CACHE_PREFIX}{digest}"


class LLMResponseCache:
    """Typed Redis helper for cached completions.

    A Redis outage degrades performance and cost but never correctness: every
    read path here fails open to a cache miss (design §6.8 rule: "a Redis
    outage degrades performance and cost but never correctness").
    """

    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, key: str) -> LLMResponse | None:
        try:
            raw = await self._redis.get(key)
        except Exception:
            logger.warning("llm.cache.unavailable", extra={"event": "llm.cache.unavailable"})
            return None
        if raw is None:
            return None
        try:
            response = LLMResponse.model_validate_json(raw)
        except Exception:
            return None
        return response.model_copy(update={"from_cache": True})

    async def set(self, key: str, response: LLMResponse) -> None:
        try:
            await self._redis.set(key, response.model_dump_json(), ex=self._ttl_seconds)
        except Exception:
            logger.warning("llm.cache.unavailable", extra={"event": "llm.cache.unavailable"})
