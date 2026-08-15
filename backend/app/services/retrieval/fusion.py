"""Reciprocal Rank Fusion (design §8.6).

RRF is chosen over score normalisation because cosine similarity and
``ts_rank`` are not on a comparable scale (design §8.6): RRF uses only rank
*position*, so it needs no per-corpus calibration.
"""

from __future__ import annotations

from uuid import UUID

from app.db.models.document_chunk import DocumentChunk
from app.services.retrieval.types import RetrievedChunk


def fuse_rankings(
    *,
    semantic_results: list[tuple[DocumentChunk, str]],
    keyword_results: list[tuple[DocumentChunk, str]],
    rrf_k: int,
    top_n: int,
) -> list[RetrievedChunk]:
    """Combine two ranked lists via ``score = Σ 1/(k + rank_i)`` (design §8.6).

    Chunks present in both lists accumulate both terms, which is exactly the
    behaviour that lets hybrid search out-rank a chunk found by only one
    path.
    """
    scores: dict[UUID, float] = {}
    semantic_rank_by_id: dict[UUID, int] = {}
    keyword_rank_by_id: dict[UUID, int] = {}
    chunk_by_id: dict[UUID, DocumentChunk] = {}
    filename_by_id: dict[UUID, str] = {}

    for rank, (chunk, filename) in enumerate(semantic_results, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (rrf_k + rank)
        semantic_rank_by_id[chunk.id] = rank
        chunk_by_id[chunk.id] = chunk
        filename_by_id[chunk.id] = filename

    for rank, (chunk, filename) in enumerate(keyword_results, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (rrf_k + rank)
        keyword_rank_by_id[chunk.id] = rank
        chunk_by_id.setdefault(chunk.id, chunk)
        filename_by_id.setdefault(chunk.id, filename)

    ordered_ids = sorted(scores.keys(), key=lambda chunk_id: scores[chunk_id], reverse=True)

    fused: list[RetrievedChunk] = []
    for fused_rank, chunk_id in enumerate(ordered_ids[:top_n], start=1):
        chunk = chunk_by_id[chunk_id]
        fused.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_filename=filename_by_id[chunk_id],
                content=chunk.content,
                source_ref=chunk.source_ref,
                rank=fused_rank,
                semantic_rank=semantic_rank_by_id.get(chunk_id),
                keyword_rank=keyword_rank_by_id.get(chunk_id),
            )
        )
    return fused
