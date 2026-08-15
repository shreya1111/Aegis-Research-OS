"""Hybrid retrieval orchestration (design §6.4 "RetrievalService", §4.2, §8.6).

Owns the full path from a query string to a ranked, cited candidate set:
embed → vector search + FTS search → RRF fusion → metadata filters →
optional re-rank → citation map. Both Phase 4's single-shot RAG endpoint and
Phase 5's Retrieval agent call this service, so the retrieval behaviour is
identical regardless of which pipeline invoked it.
"""

from __future__ import annotations

from uuid import UUID

from app.db.repositories.document_chunk_repository import DocumentChunkRepository
from app.services.embedding_service import EmbeddingService
from app.services.retrieval.fusion import fuse_rankings
from app.services.retrieval.reranker import CrossEncoderReranker
from app.services.retrieval.types import RetrievalFilters, RetrievedChunk


class RetrievalService:
    """Hybrid semantic + keyword search, scoped to one project at a time."""

    def __init__(
        self,
        *,
        chunk_repository: DocumentChunkRepository,
        embedding_service: EmbeddingService,
        reranker: CrossEncoderReranker | None,
        top_k: int,
        top_n: int,
        rrf_k: int,
        rerank_enabled: bool,
    ) -> None:
        self._chunks = chunk_repository
        self._embeddings = embedding_service
        self._reranker = reranker
        self._top_k = top_k
        self._top_n = top_n
        self._rrf_k = rrf_k
        self._rerank_enabled = rerank_enabled

    async def hybrid_search(
        self,
        *,
        project_id: UUID,
        query: str,
        filters: RetrievalFilters | None = None,
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        """Run the full hybrid pipeline for one query, project-scoped
        (design §8.6 flowchart)."""
        filters = filters or RetrievalFilters()
        query_embedding = self._embeddings.embed_query(query)

        semantic_results = await self._chunks.semantic_search(
            project_id=project_id,
            query_embedding=query_embedding,
            top_k=self._top_k,
            document_ids=filters.document_ids,
            uploaded_after=filters.uploaded_after,
            uploaded_before=filters.uploaded_before,
        )
        keyword_results = await self._chunks.keyword_search(
            project_id=project_id,
            query=query,
            top_k=self._top_k,
            document_ids=filters.document_ids,
            uploaded_after=filters.uploaded_after,
            uploaded_before=filters.uploaded_before,
        )

        effective_top_n = top_n or self._top_n
        fused = fuse_rankings(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            rrf_k=self._rrf_k,
            top_n=effective_top_n,
        )

        if self._rerank_enabled and self._reranker is not None:
            return self._reranker.rerank(query, fused)
        return fused

    async def get_chunks_for_project(
        self, chunk_ids: list[UUID], *, project_id: UUID
    ) -> list[RetrievedChunk]:
        """Resolve chunk ids back to their content, project-scoped
        (design §9.3 rule 3). Used when re-hydrating citations for display."""
        chunks = await self._chunks.get_by_ids_for_project(chunk_ids, project_id=project_id)
        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_filename="",
                content=chunk.content,
                source_ref=chunk.source_ref,
                rank=0,
            )
            for chunk in chunks
        ]
