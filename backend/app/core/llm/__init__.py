"""LLM provider abstraction (design §4.1).

All LLM traffic passes through exactly one interface: :class:`LLMProvider`. No
agent, service, or router imports a provider SDK directly.
"""

from app.core.llm.provider import LLMProvider, LLMResponse, Message, ModelTier
from app.core.llm.registry import get_llm_provider

__all__ = ["LLMProvider", "LLMResponse", "Message", "ModelTier", "get_llm_provider"]
