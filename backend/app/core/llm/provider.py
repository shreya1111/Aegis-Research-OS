"""The single LLM interface every agent and service depends on (design §4.1).

Concrete providers (``OpenAIProvider``, ``GeminiProvider``, ``SambaNovaProvider``)
implement this protocol. Switching providers is a configuration change
(``LLM_PROVIDER=openai|gemini|sambanova``); it never touches agent or business
logic.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

ModelTier = Literal["fast", "strong"]


class Message(BaseModel):
    """One turn in the prompt sent to the model."""

    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user", "assistant"]
    content: str


class ToolCall(BaseModel):
    """A tool invocation the model requested (design §4.7)."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    arguments: dict[str, object] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Every call returns tokens, model, and cost so the orchestrator can
    write them into ``agent_traces`` (design §4.1)."""

    model_config = ConfigDict(frozen=True)

    text: str
    tokens_in: int
    tokens_out: int
    model_used: str
    estimated_cost_usd: float
    #: Populated when the model requested tool calls instead of (or alongside)
    #: a text answer (design §4.7). Empty for a plain completion.
    tool_calls: list[ToolCall] = Field(default_factory=list)
    #: ``True`` when this response was served from the Redis LLM cache
    #: (design §6.8) — a cache hit is a zero-cost trace step.
    from_cache: bool = False


class LLMProvider(Protocol):
    """The interface every agent and service depends on (design §4.1)."""

    async def complete(
        self,
        messages: list[Message],
        model_tier: ModelTier,
        max_tokens: int,
        tools: list[dict[str, object]] | None = None,
    ) -> LLMResponse: ...
