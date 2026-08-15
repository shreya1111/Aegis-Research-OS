"""Redis cache for external-source lookups (design §6.8, §4.7).

Key: ``ext:{provider}:{sha256(normalised_query)}``. Repeated academic/web
lookups across agents and runs are the most wasteful pattern in a
multi-agent system, so every connector routes through this cache.
"""

from __future__ import annotations

import hashlib
import json

from redis.asyncio import Redis

from app.core.logging import get_logger
from app.services.retrieval.types import ExternalSource

logger = get_logger(__name__)

_PREFIX = "ext:"


def _normalise_query(query: str) -> str:
    return " ".join(query.lower().split())


def build_cache_key(provider: str, query: str) -> str:
    digest = hashlib.sha256(_normalise_query(query).encode("utf-8")).hexdigest()
    return f"{_PREFIX}{provider}:{digest}"


class ExternalSourceCache:
    """Typed Redis helper for cached external-source results.

    Fails open to a cache miss on any Redis error (design §6.8: "a Redis
    outage degrades performance and cost but never correctness").
    """

    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, key: str) -> list[ExternalSource] | None:
        try:
            raw = await self._redis.get(key)
        except Exception:
            logger.warning(
                "external_source.cache.unavailable",
                extra={"event": "external_source.cache.unavailable"},
            )
            return None
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
            return [ExternalSource(**item) for item in payload]
        except (ValueError, TypeError):
            return None

    async def set(self, key: str, sources: list[ExternalSource]) -> None:
        try:
            payload = json.dumps([source.__dict__ for source in sources])
            await self._redis.set(key, payload, ex=self._ttl_seconds)
        except Exception:
            logger.warning(
                "external_source.cache.unavailable",
                extra={"event": "external_source.cache.unavailable"},
            )
