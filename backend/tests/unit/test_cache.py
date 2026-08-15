"""Unit tests for the Redis-backed denylist and rate limiter, using fakeredis."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.cache import RateLimiter, TokenDenylist


@pytest.fixture
async def redis() -> AsyncIterator[FakeRedis]:
    client = FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.mark.unit
async def test_token_is_not_revoked_before_being_added(redis: FakeRedis) -> None:
    denylist = TokenDenylist(redis)
    assert await denylist.is_revoked("jti-1") is False


@pytest.mark.unit
async def test_revoked_token_is_reported_as_revoked(redis: FakeRedis) -> None:
    denylist = TokenDenylist(redis)
    await denylist.revoke("jti-1", ttl_seconds=60)
    assert await denylist.is_revoked("jti-1") is True


@pytest.mark.unit
async def test_revoke_with_non_positive_ttl_is_a_no_op(redis: FakeRedis) -> None:
    denylist = TokenDenylist(redis)
    await denylist.revoke("jti-1", ttl_seconds=0)
    assert await denylist.is_revoked("jti-1") is False


@pytest.mark.unit
async def test_denylist_check_fails_open_when_redis_is_unavailable() -> None:
    class BrokenRedis:
        async def exists(self, *_args: object, **_kwargs: object) -> int:
            raise ConnectionError("redis is down")

    denylist = TokenDenylist(BrokenRedis())  # type: ignore[arg-type]
    assert await denylist.is_revoked("jti-1") is False


@pytest.mark.unit
async def test_rate_limiter_allows_requests_within_the_limit(redis: FakeRedis) -> None:
    limiter = RateLimiter(redis)
    for _ in range(5):
        allowed = await limiter.check("scope", "id-1", limit=5, window_seconds=60)
        assert allowed is True


@pytest.mark.unit
async def test_rate_limiter_blocks_requests_over_the_limit(redis: FakeRedis) -> None:
    limiter = RateLimiter(redis)
    for _ in range(5):
        await limiter.check("scope", "id-1", limit=5, window_seconds=60)

    assert await limiter.check("scope", "id-1", limit=5, window_seconds=60) is False


@pytest.mark.unit
async def test_rate_limiter_tracks_identifiers_independently(redis: FakeRedis) -> None:
    limiter = RateLimiter(redis)
    for _ in range(5):
        await limiter.check("scope", "id-1", limit=5, window_seconds=60)

    assert await limiter.check("scope", "id-2", limit=5, window_seconds=60) is True


@pytest.mark.unit
async def test_rate_limiter_fails_open_when_redis_is_unavailable() -> None:
    class BrokenRedis:
        async def incr(self, *_args: object, **_kwargs: object) -> int:
            raise ConnectionError("redis is down")

    limiter = RateLimiter(BrokenRedis())  # type: ignore[arg-type]
    assert await limiter.check("scope", "id-1", limit=1, window_seconds=60) is True
