"""Cross-encoder re-ranking (design §8.7).

An optional refinement step over the fused top-K before context assembly. A
bi-encoder (used for the initial semantic search) embeds query and chunk
independently; a cross-encoder scores the pair jointly and is substantially
better at judging genuine relevance — at a latency cost, which is why it is
toggleable (design §8.7).
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.core.logging import get_logger
from app.services.retrieval.types import RetrievedChunk

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _cached_cross_encoder(model_name: str) -> CrossEncoder:
    logger.info(
        "reranker.model.loading", extra={"event": "reranker.model.loading", "model": model_name}
    )
    encoder: CrossEncoder = CrossEncoder(model_name)
    logger.info(
        "reranker.model.loaded", extra={"event": "reranker.model.loaded", "model": model_name}
    )
    return encoder


class CrossEncoderReranker:
    """Reorders a bounded candidate set by joint query-chunk relevance
    (design §8.7: "operates on tens of candidates, never on the corpus")."""

    def __init__(self, *, model_name: str) -> None:
        self._model_name = model_name

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return []
        encoder = _cached_cross_encoder(self._model_name)
        pairs = [(query, chunk.content) for chunk in chunks]
        scores = encoder.predict(pairs)  # type: ignore[arg-type]

        scored = sorted(
            zip(chunks, scores, strict=True), key=lambda pair: float(pair[1]), reverse=True
        )
        return [
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_filename=chunk.document_filename,
                content=chunk.content,
                source_ref=chunk.source_ref,
                rank=new_rank,
                semantic_rank=chunk.semantic_rank,
                keyword_rank=chunk.keyword_rank,
                rerank_score=float(score),
            )
            for new_rank, (chunk, score) in enumerate(scored, start=1)
        ]
