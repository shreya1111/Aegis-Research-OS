"""Embedding generation (design §4.3, §6.4).

The sentence-transformers model is loaded once per process and reused for
every chunk and query — "the same model for both, always" (design §4.3), which
is what makes semantic search correct. Model loading is expensive (seconds),
so :func:`get_embedding_service` caches the instance.
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Loads the configured sentence-transformers model once and batch-encodes
    chunks and queries (design §6.4 service table)."""

    def __init__(self, *, model_name: str, batch_size: int) -> None:
        self._model_name = model_name
        self._batch_size = batch_size
        logger.info(
            "embedding.model.loading",
            extra={"event": "embedding.model.loading", "model": model_name},
        )
        self._model = SentenceTransformer(model_name)
        logger.info(
            "embedding.model.loaded",
            extra={"event": "embedding.model.loaded", "model": model_name},
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return int(self._model.get_embedding_dimension())

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch-encode multiple texts (design §4.3: "batched during background
        ingestion to amortise model overhead")."""
        if not texts:
            return []
        vectors = self._model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        """Encode a single query with the same model used for chunks
        (design §4.3), so semantic search compares like with like."""
        return self.embed_texts([text])[0]


@lru_cache(maxsize=1)
def _cached_embedding_service(model_name: str, batch_size: int) -> EmbeddingService:
    return EmbeddingService(model_name=model_name, batch_size=batch_size)


def get_embedding_service(settings: Settings | None = None) -> EmbeddingService:
    """Return the process-wide embedding service singleton.

    Cached by ``(model_name, batch_size)`` so a settings override in tests
    produces an independent instance rather than reusing a differently
    configured one.
    """
    settings = settings or get_settings()
    return _cached_embedding_service(settings.embedding_model, settings.embedding_batch_size)
