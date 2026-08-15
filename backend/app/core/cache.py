"""Typed Redis helpers (design §6.8, §9.6).

Two concerns live here in Phase 1: the access-token revocation denylist and the
fixed-window rate limiter backing auth throttling. Both degrade gracefully — a
Redis outage must never turn into a request failure that blocks legitimate users
(design §9.6, A33), except where failing open would itself be a hazard.
"""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_DENYLIST_PREFIX = "auth:denylist:"
_RATE_LIMIT_PREFIX = "rl:"


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """Return the process-wide async Redis client, created once."""
    settings = get_settings()
    return Redis.from_url(str(settings.redis_url), decode_responses=True)


def reset_redis_client_cache() -> None:
    """Drop the cached client. Used by tests that inject a fake client."""
    get_redis_client.cache_clear()


class TokenDenylist:
    """Redis-backed revocation list for access tokens (design §9.2).

    On logout, a token's ``jti`` is added with a TTL matching its remaining
    lifetime, so the denylist never grows unbounded. If Redis is unreachable,
    revocation checks fail open — a token that cannot be checked is treated as
    not revoked, since an outage must not lock every user out of the entire
    API. This is the documented limitation in design §9.2.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def revoke(self, jti: str, *, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        await self._redis.set(f"{_DENYLIST_PREFIX}{jti}", "1", ex=ttl_seconds)

    async def is_revoked(self, jti: str) -> bool:
        try:
            return await self._redis.exists(f"{_DENYLIST_PREFIX}{jti}") > 0
        except Exception:
            logger.warning(
                "cache.denylist.unavailable",
                extra={"event": "cache.denylist.unavailable"},
            )
            return False


class RateLimiter:
    """Fixed-window rate limiter (design §9.6).

    Redis outages degrade to permissive rather than blocking every request —
    an explicit availability-over-strictness trade-off for a demo-critical
    system, documented in design §9.6 and A33.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def check(self, scope: str, identifier: str, *, limit: int, window_seconds: int) -> bool:
        """Return ``True`` if the caller is within the limit for this window."""
        key = f"{_RATE_LIMIT_PREFIX}{scope}:{identifier}"
        try:
            current = await self._redis.incr(key)
            if current == 1:
                await self._redis.expire(key, window_seconds)
            return current <= limit
        except Exception:
            logger.warning(
                "cache.rate_limit.unavailable",
                extra={"event": "cache.rate_limit.unavailable", "scope": scope},
            )
            return True


def get_token_denylist() -> TokenDenylist:
    return TokenDenylist(get_redis_client())


def get_rate_limiter() -> RateLimiter:
    return RateLimiter(get_redis_client())
