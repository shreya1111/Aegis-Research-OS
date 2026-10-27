"""Selects the active :class:`LLMProvider` implementation (design §4.1).

``LLM_PROVIDER=openai|gemini|sambanova`` is the only switch. Everything above
this module depends on the :class:`LLMProvider` protocol, never a concrete
class, so changing the environment variable is the entire migration.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.cache import get_redis_client
from app.core.config import Settings, get_settings
from app.core.llm.cache import LLMResponseCache
from app.core.llm.caching_provider import CachingLLMProvider
from app.core.llm.circuit_breaker import CircuitBreaker
from app.core.llm.gemini_provider import GeminiProvider
from app.core.llm.http_chat_provider import HttpChatCompletionsProvider
from app.core.llm.provider import LLMProvider

_DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _build_provider(settings: Settings) -> LLMProvider:
    breaker = CircuitBreaker(
        failure_threshold=settings.llm_circuit_breaker_failure_threshold,
        reset_seconds=settings.llm_circuit_breaker_reset_seconds,
        name=settings.llm_provider,
    )

    if settings.llm_provider == "gemini":
        inner: LLMProvider = GeminiProvider(
            base_url=settings.llm_base_url
            if settings.llm_base_url not in {"https://api.openai.com/v1", "https://api.sambanova.ai/v1"}
            else _DEFAULT_GEMINI_BASE_URL,
            api_key=settings.llm_api_key,
            model_fast=settings.llm_model_fast,
            model_strong=settings.llm_model_strong,
            timeout_seconds=settings.llm_request_timeout_seconds,
            max_retries=settings.llm_max_retries,
            cost_per_1k_input_tokens=settings.llm_cost_per_1k_input_tokens,
            cost_per_1k_output_tokens=settings.llm_cost_per_1k_output_tokens,
            circuit_breaker=breaker,
        )
    else:
        # openai and sambanova both speak the OpenAI-compatible chat-completions
        # format; only base_url/model names differ, which is configuration.
        inner = HttpChatCompletionsProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model_fast=settings.llm_model_fast,
            model_strong=settings.llm_model_strong,
            timeout_seconds=settings.llm_request_timeout_seconds,
            max_retries=settings.llm_max_retries,
            cost_per_1k_input_tokens=settings.llm_cost_per_1k_input_tokens,
            cost_per_1k_output_tokens=settings.llm_cost_per_1k_output_tokens,
            circuit_breaker=breaker,
            provider_name=settings.llm_provider,
        )

    cache = LLMResponseCache(get_redis_client(), ttl_seconds=settings.llm_cache_ttl_seconds)
    return CachingLLMProvider(inner, cache)


@lru_cache(maxsize=1)
def _cached_provider(
    provider_name: str,
    api_key: str,
    base_url: str,
    model_fast: str,
    model_strong: str,
) -> LLMProvider:
    return _build_provider(get_settings())


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Return the process-wide provider singleton.

    Cached by every input that determines provider identity, so a settings
    override in tests produces an independent instance.
    """
    settings = settings or get_settings()
    return _cached_provider(
        settings.llm_provider,
        settings.llm_api_key,
        settings.llm_base_url,
        settings.llm_model_fast,
        settings.llm_model_strong,
    )


def reset_llm_provider_cache() -> None:
    """Drop the cached provider. Used by tests that inject a fake provider."""
    _cached_provider.cache_clear()
