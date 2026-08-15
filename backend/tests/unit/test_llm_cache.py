"""Unit tests for the LLM response cache key and Redis-backed cache
(design §4.1, §6.8)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.llm.cache import LLMResponseCache, build_cache_key
from app.core.llm.provider import LLMResponse, Message


@pytest.fixture
async def redis() -> AsyncIterator[FakeRedis]:
    client = FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.mark.unit
def test_identical_inputs_produce_the_same_cache_key() -> None:
    messages = [Message(role="user", content="What is RRF?")]

    first = build_cache_key(messages, "fast")
    second = build_cache_key(messages, "fast")

    assert first == second


@pytest.mark.unit
def test_different_model_tiers_produce_different_cache_keys() -> None:
    """Design §6.8 rule: "cache keys include every input that changes the
    output (notably model_tier...)"."""
    messages = [Message(role="user", content="What is RRF?")]

    fast_key = build_cache_key(messages, "fast")
    strong_key = build_cache_key(messages, "strong")

    assert fast_key != strong_key


@pytest.mark.unit
def test_different_document_ids_produce_different_cache_keys() -> None:
    """Design §6.8 rule: keys include "the relevant document IDs"."""
    messages = [Message(role="user", content="Summarise this.")]

    key_a = build_cache_key(messages, "fast", document_ids=["doc-a"])
    key_b = build_cache_key(messages, "fast", document_ids=["doc-b"])

    assert key_a != key_b


@pytest.mark.unit
def test_document_id_order_does_not_change_the_cache_key() -> None:
    messages = [Message(role="user", content="Summarise this.")]

    key_one = build_cache_key(messages, "fast", document_ids=["a", "b"])
    key_two = build_cache_key(messages, "fast", document_ids=["b", "a"])

    assert key_one == key_two


@pytest.mark.unit
async def test_cache_miss_returns_none(redis: FakeRedis) -> None:
    cache = LLMResponseCache(redis, ttl_seconds=60)

    assert await cache.get("llm:missing") is None


@pytest.mark.unit
async def test_cache_hit_is_marked_from_cache(redis: FakeRedis) -> None:
    cache = LLMResponseCache(redis, ttl_seconds=60)
    response = LLMResponse(
        text="answer", tokens_in=10, tokens_out=5, model_used="gpt-4o-mini", estimated_cost_usd=0.01
    )
    await cache.set("llm:key", response)

    cached = await cache.get("llm:key")

    assert cached is not None
    assert cached.text == "answer"
    assert cached.from_cache is True


@pytest.mark.unit
async def test_cache_fails_open_when_redis_is_unavailable() -> None:
    class BrokenRedis:
        async def get(self, *_args: object, **_kwargs: object) -> str:
            raise ConnectionError("redis is down")

        async def set(self, *_args: object, **_kwargs: object) -> None:
            raise ConnectionError("redis is down")

    cache = LLMResponseCache(BrokenRedis(), ttl_seconds=60)  # type: ignore[arg-type]
    response = LLMResponse(
        text="x", tokens_in=1, tokens_out=1, model_used="m", estimated_cost_usd=0.0
    )

    assert await cache.get("llm:key") is None
    await cache.set("llm:key", response)
