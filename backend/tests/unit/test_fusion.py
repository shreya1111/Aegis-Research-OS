"""Unit tests for reciprocal rank fusion (design §8.6)."""

from __future__ import annotations

import uuid

import pytest

from app.db.models.document_chunk import DocumentChunk
from app.services.retrieval.fusion import fuse_rankings


def _chunk(content: str = "content") -> DocumentChunk:
    return DocumentChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        chunk_index=0,
        content=content,
        source_ref={},
    )


@pytest.mark.unit
def test_a_chunk_found_by_both_paths_outranks_one_found_by_only_one() -> None:
    """Design §8.6: RRF should let a chunk present in both rankings out-rank
    a chunk found by only one path, even if that chunk ranked #1 somewhere."""
    shared = _chunk("shared")
    semantic_only = _chunk("semantic only")

    fused = fuse_rankings(
        semantic_results=[(semantic_only, "a.pdf"), (shared, "b.pdf")],
        keyword_results=[(shared, "b.pdf")],
        rrf_k=60,
        top_n=10,
    )

    assert fused[0].chunk_id == shared.id


@pytest.mark.unit
def test_fusion_respects_top_n() -> None:
    chunks = [_chunk(f"chunk {i}") for i in range(5)]
    semantic_results = [(chunk, "a.pdf") for chunk in chunks]

    fused = fuse_rankings(semantic_results=semantic_results, keyword_results=[], rrf_k=60, top_n=2)

    assert len(fused) == 2


@pytest.mark.unit
def test_fused_rank_is_contiguous_starting_at_one() -> None:
    chunks = [_chunk(f"chunk {i}") for i in range(3)]
    semantic_results = [(chunk, "a.pdf") for chunk in chunks]

    fused = fuse_rankings(semantic_results=semantic_results, keyword_results=[], rrf_k=60, top_n=10)

    assert [chunk.rank for chunk in fused] == [1, 2, 3]


@pytest.mark.unit
def test_semantic_and_keyword_only_chunks_both_carry_their_source_rank() -> None:
    semantic_only = _chunk("semantic")
    keyword_only = _chunk("keyword")

    fused = fuse_rankings(
        semantic_results=[(semantic_only, "a.pdf")],
        keyword_results=[(keyword_only, "b.pdf")],
        rrf_k=60,
        top_n=10,
    )

    by_id = {chunk.chunk_id: chunk for chunk in fused}
    assert by_id[semantic_only.id].semantic_rank == 1
    assert by_id[semantic_only.id].keyword_rank is None
    assert by_id[keyword_only.id].keyword_rank == 1
    assert by_id[keyword_only.id].semantic_rank is None


@pytest.mark.unit
def test_empty_inputs_produce_an_empty_result() -> None:
    assert fuse_rankings(semantic_results=[], keyword_results=[], rrf_k=60, top_n=10) == []
