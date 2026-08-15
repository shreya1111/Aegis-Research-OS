"""Single-shot hybrid RAG (design §4.2 "Phase 4 — single-shot RAG", §8.8).

One question → hybrid retrieval → cited answer. This is the fast path: a
simple factual lookup does not pay the cost of a full agent graph. Every run
still writes ``agent_traces`` rows so its cost is visible in the same
observability spine Phase 5 uses.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.agents.tracing import traced_step
from app.core.errors import NotFoundError
from app.core.llm.provider import LLMProvider, Message
from app.db.models.conversation import Conversation
from app.db.models.message import MessageRole
from app.db.repositories.agent_trace_repository import AgentTraceRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository
from app.services.retrieval.citation import (
    build_citation_map,
    to_message_citations,
    validate_citations,
)
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.types import CitationMap, RetrievalFilters, RetrievedChunk

_SYSTEM_PROMPT = (
    "You are a research assistant. Answer the user's question using only the "
    "numbered sources provided below. Cite every claim inline using the "
    "source's exact marker in square brackets, e.g. [Doc 1, p.2]. Never cite "
    "a marker that was not supplied. If the sources do not contain enough "
    "information to answer, say so explicitly rather than guessing."
)


@dataclass(frozen=True, slots=True)
class RagAnswer:
    """The result of one single-shot RAG run."""

    run_id: UUID
    message_id: UUID
    answer: str
    citations: list[dict[str, object]]
    sources: list[RetrievedChunk]
    citation_warning: bool


class RagService:
    """Orchestrates the Phase 4 hybrid RAG pipeline end to end."""

    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        llm_provider: LLMProvider,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        trace_repository: AgentTraceRepository,
        max_regeneration_attempts: int,
        answer_max_tokens: int = 1000,
    ) -> None:
        self._retrieval = retrieval_service
        self._llm = llm_provider
        self._conversations = conversation_repository
        self._messages = message_repository
        self._traces = trace_repository
        self._max_regeneration_attempts = max_regeneration_attempts
        self._answer_max_tokens = answer_max_tokens

    async def answer_question(
        self,
        *,
        project_id: UUID,
        question: str,
        filters: RetrievalFilters | None = None,
        conversation_id: UUID | None = None,
    ) -> RagAnswer:
        run_id = uuid4()
        conversation = await self._resolve_conversation(
            project_id=project_id, conversation_id=conversation_id
        )

        async def retrieve() -> list[RetrievedChunk]:
            return await self._retrieval.hybrid_search(
                project_id=project_id, query=question, filters=filters
            )

        chunks = await traced_step(
            self._traces,
            run_id=run_id,
            project_id=project_id,
            agent_name="Retrieval",
            input_summary=question,
            work=retrieve,
        )
        citation_map = build_citation_map(chunks)

        answer_text, citation_warning = await self._generate_validated_answer(
            run_id, project_id=project_id, question=question, citation_map=citation_map
        )

        await self._messages.create(
            conversation_id=conversation.id, role=MessageRole.USER, content=question
        )
        citations = to_message_citations(answer_text, citation_map)
        assistant_message = await self._messages.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=answer_text,
            citations=citations,
        )
        await self._conversations.set_title_if_unset(conversation, question)
        await self._traces.attach_message(run_id, assistant_message.id, project_id=project_id)

        return RagAnswer(
            run_id=run_id,
            message_id=assistant_message.id,
            answer=answer_text,
            citations=citations,
            sources=chunks,
            citation_warning=citation_warning,
        )

    async def _resolve_conversation(
        self, *, project_id: UUID, conversation_id: UUID | None
    ) -> Conversation:
        if conversation_id is not None:
            conversation = await self._conversations.get_by_id_for_project(
                conversation_id, project_id=project_id
            )
            if conversation is None:
                raise NotFoundError("Conversation not found.")
            return conversation
        return await self._conversations.get_or_create_default(project_id=project_id)

    async def _generate_validated_answer(
        self, run_id: UUID, *, project_id: UUID, question: str, citation_map: CitationMap
    ) -> tuple[str, bool]:
        """Generate, then validate citations, regenerating on failure up to
        the configured cap; after that the answer is accepted with a warning
        flag rather than looping forever (design §4.2)."""
        context_blocks = citation_map.as_context_blocks()
        context = "\n\n".join(context_blocks) if context_blocks else "(no sources retrieved)"

        messages = [
            Message(role="system", content=_SYSTEM_PROMPT),
            Message(role="user", content=f"Sources:\n{context}\n\nQuestion: {question}"),
        ]

        attempt = 0
        answer_text = ""
        while True:
            started = time.monotonic()
            response = await self._llm.complete(messages, "strong", self._answer_max_tokens)
            latency_ms = (time.monotonic() - started) * 1000
            answer_text = response.text

            await self._traces.create(
                project_id=project_id,
                run_id=run_id,
                agent_name="Synthesis/Report-Writer",
                input_summary=question[:500],
                output_summary=answer_text[:500],
                tokens_used=response.tokens_in + response.tokens_out,
                latency_ms=latency_ms,
                estimated_cost=0.0 if response.from_cache else response.estimated_cost_usd,
                status="success",
            )

            all_valid, _unresolved = validate_citations(answer_text, citation_map)
            if all_valid or attempt >= self._max_regeneration_attempts:
                return answer_text, not all_valid
            attempt += 1
