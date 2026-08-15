"""Unit tests for the embedding service (design §4.3, §6.4).

Loads the real, small ``all-MiniLM-L6-v2`` model — no network call is made
beyond the one-time model download, which is cached locally (design: "In-process
in the backend container. No external embedding API call").
"""

from __future__ import annotations

import pytest

from app.services.embedding_service import EmbeddingService, get_embedding_service

MODEL_NAME = "all-MiniLM-L6-v2"


@pytest.fixture(scope="module")
def embedding_service() -> EmbeddingService:
    # Loaded once per test module — model load takes real wall-clock time.
    return EmbeddingService(model_name=MODEL_NAME, batch_size=8)


@pytest.mark.unit
class TestEmbeddingService:
    def test_reports_the_configured_model_name(self, embedding_service: EmbeddingService) -> None:
        assert embedding_service.model_name == MODEL_NAME

    def test_dimensions_matches_the_known_model_output_size(
        self, embedding_service: EmbeddingService
    ) -> None:
        # all-MiniLM-L6-v2 is a fixed, well-known 384-dimension model — this
        # is what `Settings.embedding_dimensions` must match (design §4.3).
        assert embedding_service.dimensions == 384

    def test_embed_texts_returns_one_vector_per_input(
        self, embedding_service: EmbeddingService
    ) -> None:
        vectors = embedding_service.embed_texts(["hello world", "goodbye world", "third text"])
        assert len(vectors) == 3
        assert all(len(vector) == 384 for vector in vectors)

    def test_embed_texts_of_empty_list_returns_empty_list(
        self, embedding_service: EmbeddingService
    ) -> None:
        assert embedding_service.embed_texts([]) == []

    def test_embed_query_returns_a_single_vector(self, embedding_service: EmbeddingService) -> None:
        vector = embedding_service.embed_query("what is the capital of France?")
        assert len(vector) == 384

    def test_same_text_produces_the_same_vector(self, embedding_service: EmbeddingService) -> None:
        """Design §4.3: "Same text + same model → same vector" (determinism)."""
        first = embedding_service.embed_query("deterministic input text")
        second = embedding_service.embed_query("deterministic input text")
        assert first == second

    def test_different_text_produces_different_vectors(
        self, embedding_service: EmbeddingService
    ) -> None:
        first = embedding_service.embed_query("cats are wonderful pets")
        second = embedding_service.embed_query("quantum mechanics is fascinating")
        assert first != second

    def test_query_and_chunk_embedding_use_the_same_model(
        self, embedding_service: EmbeddingService
    ) -> None:
        """Design §4.3: "the same model for both, always" — verified by
        confirming embed_query and embed_texts produce identical vectors for
        identical input, i.e. there is no separate code path per use case."""
        via_query = embedding_service.embed_query("shared input")
        via_batch = embedding_service.embed_texts(["shared input"])[0]
        assert via_query == via_batch


@pytest.mark.unit
def test_get_embedding_service_is_cached_by_model_and_batch_size() -> None:
    from app.core.config import Settings

    settings = Settings(embedding_model=MODEL_NAME, embedding_batch_size=8)
    first = get_embedding_service(settings)
    second = get_embedding_service(settings)
    assert first is second
