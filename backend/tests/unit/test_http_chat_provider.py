"""Unit tests for the OpenAI-compatible chat-completions provider payload."""

from __future__ import annotations

import pytest

from app.core.llm.circuit_breaker import CircuitBreaker
from app.core.llm.http_chat_provider import HttpChatCompletionsProvider
from app.core.llm.provider import Message


def _provider(provider_name: str) -> HttpChatCompletionsProvider:
    return HttpChatCompletionsProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_fast="fast-model",
        model_strong="strong-model",
        timeout_seconds=5,
        max_retries=0,
        cost_per_1k_input_tokens=0.0,
        cost_per_1k_output_tokens=0.0,
        circuit_breaker=CircuitBreaker(failure_threshold=5, reset_seconds=30, name=provider_name),
        provider_name=provider_name,
    )


async def _captured_payload(
    provider: HttpChatCompletionsProvider, monkeypatch: pytest.MonkeyPatch
) -> dict[str, object]:
    captured: dict[str, object] = {}

    async def fake_call(payload: dict[str, object]) -> dict[str, object]:
        captured.update(payload)
        return {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }

    monkeypatch.setattr(provider, "_call_with_retry", fake_call)
    await provider.complete([Message(role="user", content="hi")], "strong", 256)
    return captured


@pytest.mark.unit
async def test_openai_uses_max_completion_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = await _captured_payload(_provider("openai"), monkeypatch)

    assert payload["max_completion_tokens"] == 256
    assert "max_tokens" not in payload
    assert payload["model"] == "strong-model"


@pytest.mark.unit
async def test_other_hosts_keep_max_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = await _captured_payload(_provider("sambanova"), monkeypatch)

    assert payload["max_tokens"] == 256
    assert "max_completion_tokens" not in payload
