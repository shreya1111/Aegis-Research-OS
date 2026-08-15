"""Unit tests for the ``run:{run_id}`` Redis status cache (design §6.8)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from fakeredis.aioredis import FakeRedis

from app.services.agent_run_status import AgentRunStatusCache


@pytest.fixture
async def redis() -> AsyncIterator[FakeRedis]:
    client = FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.mark.unit
async def test_get_status_returns_none_before_any_write(redis: FakeRedis) -> None:
    cache = AgentRunStatusCache(redis, ttl_seconds=60)

    assert await cache.get_status(uuid4()) is None


@pytest.mark.unit
async def test_set_and_get_status_round_trips(redis: FakeRedis) -> None:
    cache = AgentRunStatusCache(redis, ttl_seconds=60)
    run_id = uuid4()

    await cache.set_status(run_id, "running")

    status = await cache.get_status(run_id)
    assert status == {"status": "running", "detail": ""}


@pytest.mark.unit
async def test_set_status_carries_a_detail_message(redis: FakeRedis) -> None:
    cache = AgentRunStatusCache(redis, ttl_seconds=60)
    run_id = uuid4()

    await cache.set_status(run_id, "failed", detail="retrieval failed: timeout")

    status = await cache.get_status(run_id)
    assert status == {"status": "failed", "detail": "retrieval failed: timeout"}


@pytest.mark.unit
async def test_a_later_status_overwrites_an_earlier_one(redis: FakeRedis) -> None:
    cache = AgentRunStatusCache(redis, ttl_seconds=60)
    run_id = uuid4()

    await cache.set_status(run_id, "running")
    await cache.set_status(run_id, "completed")

    status = await cache.get_status(run_id)
    assert status is not None
    assert status["status"] == "completed"


@pytest.mark.unit
async def test_set_status_fails_open_when_redis_is_unavailable() -> None:
    class BrokenRedis:
        async def set(self, *_args: object, **_kwargs: object) -> None:
            raise ConnectionError("redis is down")

    cache = AgentRunStatusCache(BrokenRedis(), ttl_seconds=60)  # type: ignore[arg-type]

    await cache.set_status(uuid4(), "running")  # must not raise


@pytest.mark.unit
async def test_get_status_fails_open_when_redis_is_unavailable() -> None:
    class BrokenRedis:
        async def get(self, *_args: object, **_kwargs: object) -> str:
            raise ConnectionError("redis is down")

    cache = AgentRunStatusCache(BrokenRedis(), ttl_seconds=60)  # type: ignore[arg-type]

    assert await cache.get_status(uuid4()) is None
