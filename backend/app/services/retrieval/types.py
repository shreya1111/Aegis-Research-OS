"""Shared data structures for hybrid retrieval (design §4.2, §8.6, §8.8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    """Metadata filters applied inside both retrieval queries (design §8.6).

    Filters shrink the candidate set rather than discarding results after
    ranking — every predicate here is composed into the SQL, not applied in
    Python.
    """

    document_ids: list[UUID] | None = None
    uploaded_after: datetime | None = None
    uploaded_before: datetime | None = None


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """One chunk surfaced by hybrid search, carrying its provenance and the
    signals that produced its final rank (design §8.6, §8.8)."""

    chunk_id: UUID
    document_id: UUID
    document_filename: str
    content: str
    source_ref: dict[str, object]
    #: Fused rank position (1 = best) after reciprocal rank fusion.
    rank: int
    #: Present only if the vector path found this chunk.
    semantic_rank: int | None = None
    #: Present only if the keyword path found this chunk.
    keyword_rank: int | None = None
    #: Cross-encoder relevance score, set only when re-ranking is enabled
    #: (design §8.7).
    rerank_score: float | None = None


@dataclass(frozen=True, slots=True)
class ExternalSource:
    """Normalised shape every external connector returns (design §4.7, §8.6).

    Agents never see provider-specific JSON — every source, regardless of
    provider, is represented identically.
    """

    title: str
    authors: list[str]
    year: int | None
    venue: str | None
    identifier: str | None
    url: str | None
    abstract: str | None
    provider: str


@dataclass(frozen=True, slots=True)
class CitationMapEntry:
    """One marker → source binding, built during context assembly
    (design §8.8 step 1)."""

    marker: str
    chunk: RetrievedChunk | None = None
    external_source: ExternalSource | None = None


@dataclass(frozen=True, slots=True)
class CitationMap:
    """The full marker → source binding for one generation call
    (design §8.8)."""

    entries: dict[str, CitationMapEntry] = field(default_factory=dict)

    def resolve(self, marker: str) -> CitationMapEntry | None:
        return self.entries.get(marker)

    def as_context_blocks(self) -> list[str]:
        """Render each source as a labelled block for the prompt."""
        blocks: list[str] = []
        for marker, entry in self.entries.items():
            if entry.chunk is not None:
                blocks.append(f"[{marker}] {entry.chunk.content}")
            elif entry.external_source is not None:
                source = entry.external_source
                blocks.append(f"[{marker}] {source.title} — {source.abstract or ''}".strip())
        return blocks
