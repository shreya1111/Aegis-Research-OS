"""Wire contracts for the hybrid RAG / agent query endpoint (design §6.1, §8.8)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.services.agent_service import AgentRunResult
from app.services.rag_service import RagAnswer


class QueryFilters(BaseModel):
    """Optional metadata filters (design §8.6): specific documents or a date
    range. Absent filters mean "search the whole project"."""

    model_config = ConfigDict(str_strip_whitespace=True)

    document_ids: list[UUID] | None = None
    uploaded_after: datetime | None = None
    uploaded_before: datetime | None = None


class QueryRequest(BaseModel):
    """Payload for ``POST /projects/{id}/query``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None
    filters: QueryFilters | None = None


class SourceRead(BaseModel):
    """One retrieved chunk, as returned alongside the answer (design §8.8 step 8)."""

    model_config = ConfigDict(frozen=True)

    chunk_id: UUID
    document_id: UUID
    document_filename: str
    content: str
    source_ref: dict[str, object]
    rank: int


class QueryResponse(BaseModel):
    """Response for ``POST /projects/{id}/query`` (design §6.1)."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    message_id: UUID
    answer: str
    citations: list[dict[str, object]]
    sources: list[SourceRead]
    #: Set when citation validation could not resolve every marker after the
    #: regeneration cap — the answer is still returned, flagged, rather than
    #: withheld (design §4.2).
    citation_warning: bool
    #: ``True`` only for agent-graph runs (design §4.2 remains the fast path
    #: and never degrades); ``False`` for every Phase 4 single-shot answer.
    pipeline: str = "rag"

    @classmethod
    def from_answer(cls, answer: RagAnswer) -> QueryResponse:
        return cls(
            run_id=answer.run_id,
            message_id=answer.message_id,
            answer=answer.answer,
            citations=answer.citations,
            sources=[
                SourceRead(
                    chunk_id=source.chunk_id,
                    document_id=source.document_id,
                    document_filename=source.document_filename,
                    content=source.content,
                    source_ref=source.source_ref,
                    rank=source.rank,
                )
                for source in answer.sources
            ],
            citation_warning=answer.citation_warning,
            pipeline="rag",
        )

    @classmethod
    def from_agent_result(cls, result: AgentRunResult) -> QueryResponse:
        return cls(
            run_id=result.run_id,
            message_id=result.message_id,
            answer=result.answer,
            citations=result.citations,
            sources=[
                SourceRead(
                    chunk_id=source.chunk_id,
                    document_id=source.document_id,
                    document_filename=source.document_filename,
                    content=source.content,
                    source_ref=source.source_ref,
                    rank=source.rank,
                )
                for source in result.sources
            ],
            citation_warning=result.citation_warning,
            pipeline="agent",
        )
