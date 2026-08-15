"""Project-level long-term memory (design §6.4 "MemoryService", §4.5).

On read, returns a compact, relevance-filtered digest of project memory —
never a raw dump, which would blow the context budget. On write, distils only
durable, source-backed conclusions; speculative or unverified statements are
never promoted (design §4.5 "Memory agent contract").
"""

from __future__ import annotations

from uuid import UUID

from app.core.llm.provider import LLMProvider, Message
from app.db.repositories.project_memory_repository import ProjectMemoryRepository

_DIGEST_PROMPT = (
    "You are maintaining a research project's long-term memory. Below are "
    "previously established facts. Produce a short digest (at most 5 bullet "
    "points) of the facts most relevant to the current question. If none are "
    "relevant, say so plainly."
)

_DISTILL_PROMPT = (
    "You are distilling durable facts from a research answer for long-term "
    "project memory. Extract only claims that are source-backed and stated "
    "with confidence — never speculative or hedged statements. Return each "
    "fact as a separate line, or return nothing if there is no durable fact "
    "to record."
)


class MemoryService:
    """Reads and writes project-level memory (design §4.5)."""

    def __init__(
        self,
        *,
        memory_repository: ProjectMemoryRepository,
        llm_provider: LLMProvider,
        digest_max_tokens: int = 300,
        distill_max_tokens: int = 300,
    ) -> None:
        self._memory = memory_repository
        self._llm = llm_provider
        self._digest_max_tokens = digest_max_tokens
        self._distill_max_tokens = distill_max_tokens

    async def read_digest(self, *, project_id: UUID, question: str) -> str:
        """Return a relevance-filtered digest for the current request
        (design §4.5: "never a raw dump")."""
        facts = await self._memory.list_for_project(project_id, limit=50)
        if not facts:
            return "(no established project memory yet)"

        facts_block = "\n".join(f"- {fact.fact}" for fact in facts)
        messages = [
            Message(role="system", content=_DIGEST_PROMPT),
            Message(
                role="user",
                content=f"Established facts:\n{facts_block}\n\nCurrent question: {question}",
            ),
        ]
        response = await self._llm.complete(messages, "fast", self._digest_max_tokens)
        return response.text

    async def write_facts(
        self, *, project_id: UUID, answer: str, citations: list[dict[str, object]]
    ) -> list[str]:
        """Distil durable facts from a synthesised answer and persist them
        with their citations (design §4.5). Returns the facts written."""
        if not answer.strip():
            return []

        messages = [
            Message(role="system", content=_DISTILL_PROMPT),
            Message(role="user", content=answer),
        ]
        response = await self._llm.complete(messages, "fast", self._distill_max_tokens)
        candidate_facts = [line.strip("-• ").strip() for line in response.text.splitlines()]
        facts = [fact for fact in candidate_facts if fact]

        for fact in facts:
            await self._memory.create(project_id=project_id, fact=fact, citations=citations)
        return facts
