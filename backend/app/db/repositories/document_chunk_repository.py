"""Query object for the ``document_chunks`` aggregate (design §6.6, §7.5).

Bulk creation is used by ingestion; project-scoped reads are the foundation
Phase 4's hybrid retrieval builds on. Every read requires ``project_id``
(design §9.3 rule 3, §7.5) — there is no method that returns chunks across
projects.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.services.ingestion.types import Chunk


class DocumentChunkRepository:
    """Persistence for :class:`DocumentChunk`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _metadata_filters(
        self,
        *,
        document_ids: list[UUID] | None,
        uploaded_after: datetime | None,
        uploaded_before: datetime | None,
    ) -> list[ColumnElement[bool]]:
        """Build the metadata predicates shared by both retrieval queries
        (design §8.6: filters shrink the candidate set inside the query)."""
        predicates: list[ColumnElement[bool]] = []
        if document_ids:
            predicates.append(DocumentChunk.document_id.in_(document_ids))
        if uploaded_after is not None or uploaded_before is not None:
            predicates.append(DocumentChunk.document_id == Document.id)
            if uploaded_after is not None:
                predicates.append(Document.uploaded_at >= uploaded_after)
            if uploaded_before is not None:
                predicates.append(Document.uploaded_at <= uploaded_before)
        return predicates

    async def semantic_search(
        self,
        *,
        project_id: UUID,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[UUID] | None = None,
        uploaded_after: datetime | None = None,
        uploaded_before: datetime | None = None,
    ) -> list[tuple[DocumentChunk, str]]:
        """Cosine-similarity search, project-scoped, ordered nearest-first
        (design §4.2, §8.6). Returns chunks paired with their document's
        filename so callers do not need a second round trip.

        The tenancy scope (``project_id``) is filtered inside this query on
        the denormalised column (design §7.5) — there is no cross-project
        result possible.
        """
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        statement = (
            select(DocumentChunk, Document.filename)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.project_id == project_id,
                DocumentChunk.embedding.is_not(None),
                *self._metadata_filters(
                    document_ids=document_ids,
                    uploaded_after=uploaded_after,
                    uploaded_before=uploaded_before,
                ),
            )
            .order_by(distance)
            .limit(top_k)
        )
        result = await self._session.execute(statement)
        return [(row[0], row[1]) for row in result.all()]

    async def keyword_search(
        self,
        *,
        project_id: UUID,
        query: str,
        top_k: int,
        document_ids: list[UUID] | None = None,
        uploaded_after: datetime | None = None,
        uploaded_before: datetime | None = None,
    ) -> list[tuple[DocumentChunk, str]]:
        """Postgres full-text search over ``content_tsv``, ranked by
        ``ts_rank`` (design §7.4, §8.6) — the keyword half of hybrid
        retrieval, scoped identically to :meth:`semantic_search`.
        """
        tsquery = func.plainto_tsquery("english", query)
        rank = func.ts_rank(DocumentChunk.content_tsv, tsquery)
        statement = (
            select(DocumentChunk, Document.filename)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.project_id == project_id,
                DocumentChunk.content_tsv.op("@@")(tsquery),
                *self._metadata_filters(
                    document_ids=document_ids,
                    uploaded_after=uploaded_after,
                    uploaded_before=uploaded_before,
                ),
            )
            .order_by(rank.desc())
            .limit(top_k)
        )
        result = await self._session.execute(statement)
        return [(row[0], row[1]) for row in result.all()]

    async def get_by_ids_for_project(
        self, chunk_ids: list[UUID], *, project_id: UUID
    ) -> list[DocumentChunk]:
        """Fetch chunks by id, scoped to a project (design §9.3 rule 3).

        Used to resolve neighbour chunks and to re-validate that emitted
        citation markers still point at genuinely retrieved chunks.
        """
        if not chunk_ids:
            return []
        statement = select(DocumentChunk).where(
            DocumentChunk.id.in_(chunk_ids), DocumentChunk.project_id == project_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def bulk_create(
        self,
        *,
        document_id: UUID,
        project_id: UUID,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> list[DocumentChunk]:
        """Persist every chunk of a document with its embedding in one batch.

        ``chunks`` and ``embeddings`` must be the same length and index-aligned
        (produced together by the ingestion pipeline).
        """
        rows = [
            DocumentChunk(
                document_id=document_id,
                project_id=project_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=embedding,
                source_ref=chunk.source_ref,
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return rows

    async def delete_for_document(self, document_id: UUID) -> None:
        """Remove all chunks for a document.

        Used before re-ingestion so a retry after a crash cannot produce
        duplicates (design §8.1: "deletes and rebuilds its chunks rather than
        appending").
        """
        statement = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        await self._session.execute(statement)
        await self._session.flush()

    async def count_for_document(self, document_id: UUID) -> int:
        statement = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self._session.execute(statement)
        return len(result.scalars().all())
