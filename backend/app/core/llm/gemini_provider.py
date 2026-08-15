"""Google Gemini provider (design §4.1, ``LLM_PROVIDER=gemini``).

Gemini's ``generateContent`` endpoint has a different request/response shape
than the OpenAI-compatible chat-completions family, so it gets its own thin
adapter. It still returns the same :class:`LLMResponse` and applies the same
retry/circuit-breaker discipline, so nothing above this layer needs to know
which provider is active.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, cast

import httpx

from app.core.errors import LLMProviderError
from app.core.llm.circuit_breaker import CircuitBreaker
from app.core.llm.errors import FatalProviderError, TransientProviderError
from app.core.llm.provider import LLMResponse, Message, ModelTier
from app.core.logging import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

#: Gemini has no "system" role; system messages are folded into the first user
#: turn via `systemInstruction`.
_ROLE_MAP = {"user": "user", "assistant": "model"}


class GeminiProvider:
    """Talks to the Google Generative Language API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_fast: str,
        model_strong: str,
        timeout_seconds: float,
        max_retries: int,
        cost_per_1k_input_tokens: float,
        cost_per_1k_output_tokens: float,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_by_tier: dict[ModelTier, str] = {"fast": model_fast, "strong": model_strong}
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._cost_per_1k_input = cost_per_1k_input_tokens
        self._cost_per_1k_output = cost_per_1k_output_tokens
        self._circuit_breaker = circuit_breaker

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        return (tokens_in / 1000) * self._cost_per_1k_input + (
            tokens_out / 1000
        ) * self._cost_per_1k_output

    async def complete(
        self,
        messages: list[Message],
        model_tier: ModelTier,
        max_tokens: int,
        tools: list[dict[str, object]] | None = None,
    ) -> LLMResponse:
        self._circuit_breaker.before_call()
        model = self._model_by_tier[model_tier]

        system_parts = [m.content for m in messages if m.role == "system"]
        contents = [
            {"role": _ROLE_MAP[m.role], "parts": [{"text": m.content}]}
            for m in messages
            if m.role != "system"
        ]
        payload: dict[str, object] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}

        try:
            body = await self._call_with_retry(model, payload)
        except (TransientProviderError, FatalProviderError) as error:
            self._circuit_breaker.on_failure()
            raise LLMProviderError("The Gemini provider is currently unavailable.") from error

        self._circuit_breaker.on_success()
        return self._parse_response(body, model)

    async def _call_with_retry(self, model: str, payload: dict[str, object]) -> dict[str, object]:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._call_once(model, payload)
            except TransientProviderError as error:
                last_error = error
                if attempt == self._max_retries:
                    break
                delay = min(2**attempt, 8) + random.uniform(0, 0.5)  # noqa: S311
                logger.warning(
                    "llm.provider.retry",
                    extra={
                        "event": "llm.provider.retry",
                        "provider": "gemini",
                        "attempt": attempt + 1,
                    },
                )
                await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    async def _call_once(self, model: str, payload: dict[str, object]) -> dict[str, object]:
        url = f"{self._base_url}/models/{model}:generateContent?key={self._api_key}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, json=payload)
        except httpx.TimeoutException as error:
            raise TransientProviderError("Request to Gemini timed out.") from error
        except httpx.HTTPError as error:
            raise TransientProviderError("Network error calling Gemini.") from error

        if response.status_code == 200:
            parsed: dict[str, object] = response.json()
            return parsed
        if response.status_code in _RETRYABLE_STATUS_CODES:
            raise TransientProviderError(f"Retryable HTTP {response.status_code}")
        raise FatalProviderError(f"Non-retryable HTTP {response.status_code}: {response.text}")

    def _parse_response(self, body: dict[str, object], model: str) -> LLMResponse:
        candidates = cast("list[dict[str, Any]]", body.get("candidates", []))
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts)

        usage = cast("dict[str, Any]", body.get("usageMetadata", {}))
        tokens_in = int(usage.get("promptTokenCount", 0))
        tokens_out = int(usage.get("candidatesTokenCount", 0))

        return LLMResponse(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model_used=model,
            estimated_cost_usd=self._estimate_cost(tokens_in, tokens_out),
        )
