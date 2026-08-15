"""OpenAI-compatible chat-completions provider (design §4.1).

Backs ``LLM_PROVIDER=openai`` and ``LLM_PROVIDER=sambanova`` — both expose an
OpenAI-compatible ``/chat/completions`` endpoint, so one HTTP client
implementation serves both; only ``base_url`` and the API key differ, which is
already a configuration concern (design §4.1: "switching providers never
touches agent or business logic").

Resilience owned here per design §4.1: bounded retry with exponential backoff
on transient errors, and a circuit breaker so a down provider degrades the run
rather than crashing it.
"""

from __future__ import annotations

import asyncio
import json
import random
from typing import Any, cast

import httpx

from app.core.errors import LLMProviderError
from app.core.llm.circuit_breaker import CircuitBreaker
from app.core.llm.errors import FatalProviderError, TransientProviderError
from app.core.llm.provider import LLMResponse, Message, ModelTier, ToolCall
from app.core.logging import get_logger

logger = get_logger(__name__)

#: HTTP statuses worth retrying — request timeouts, rate limits, and server
#: errors are transient; anything else (bad request, auth failure) is fatal.
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class HttpChatCompletionsProvider:
    """Talks to any OpenAI-compatible ``/chat/completions`` endpoint."""

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
        provider_name: str,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_by_tier: dict[ModelTier, str] = {"fast": model_fast, "strong": model_strong}
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._cost_per_1k_input = cost_per_1k_input_tokens
        self._cost_per_1k_output = cost_per_1k_output_tokens
        self._circuit_breaker = circuit_breaker
        self._provider_name = provider_name

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
        payload: dict[str, object] = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        try:
            body = await self._call_with_retry(payload)
        except (TransientProviderError, FatalProviderError) as error:
            self._circuit_breaker.on_failure()
            raise LLMProviderError(
                f"The {self._provider_name} provider is currently unavailable."
            ) from error

        self._circuit_breaker.on_success()
        return self._parse_response(body, model)

    async def _call_with_retry(self, payload: dict[str, object]) -> dict[str, object]:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._call_once(payload)
            except TransientProviderError as error:
                last_error = error
                if attempt == self._max_retries:
                    break
                # Exponential backoff with jitter, capped so a slow provider
                # cannot stall the run indefinitely.
                delay = min(2**attempt, 8) + random.uniform(0, 0.5)  # noqa: S311
                logger.warning(
                    "llm.provider.retry",
                    extra={
                        "event": "llm.provider.retry",
                        "provider": self._provider_name,
                        "attempt": attempt + 1,
                        "delay_seconds": delay,
                    },
                )
                await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    async def _call_once(self, payload: dict[str, object]) -> dict[str, object]:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
        except httpx.TimeoutException as error:
            raise TransientProviderError("Request to LLM provider timed out.") from error
        except httpx.HTTPError as error:
            raise TransientProviderError("Network error calling LLM provider.") from error

        if response.status_code == 200:
            parsed: dict[str, object] = response.json()
            return parsed
        if response.status_code in _RETRYABLE_STATUS_CODES:
            raise TransientProviderError(f"Retryable HTTP {response.status_code}")
        raise FatalProviderError(f"Non-retryable HTTP {response.status_code}: {response.text}")

    def _parse_response(self, body: dict[str, object], model: str) -> LLMResponse:
        choices = cast("list[dict[str, Any]]", body.get("choices", []))
        message = choices[0]["message"] if choices else {}
        text = message.get("content") or ""

        tool_calls: list[ToolCall] = []
        for raw_call in message.get("tool_calls", []) or []:
            function = raw_call.get("function", {})
            arguments_raw = function.get("arguments", "{}")
            try:
                arguments = json.loads(arguments_raw) if isinstance(arguments_raw, str) else {}
            except (ValueError, TypeError):
                arguments = {}
            tool_calls.append(
                ToolCall(
                    id=raw_call.get("id", ""),
                    name=function.get("name", ""),
                    arguments=arguments,
                )
            )

        usage = cast("dict[str, Any]", body.get("usage", {}))
        tokens_in = int(usage.get("prompt_tokens", 0))
        tokens_out = int(usage.get("completion_tokens", 0))

        return LLMResponse(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model_used=model,
            estimated_cost_usd=self._estimate_cost(tokens_in, tokens_out),
            tool_calls=tool_calls,
        )
