"""Unit tests for token-aware chunking (design §8.3, FR-C6)."""

from __future__ import annotations

import pytest

from app.services.ingestion.chunking import chunk_document
from app.services.ingestion.types import ExtractedDocument, ExtractedPage


def _document(*page_texts: str) -> ExtractedDocument:
    return ExtractedDocument(
        pages=[ExtractedPage(page_number=i + 1, text=text) for i, text in enumerate(page_texts)]
    )


@pytest.mark.unit
class TestChunkDocument:
    def test_empty_document_produces_no_chunks(self) -> None:
        assert chunk_document(_document(""), chunk_tokens=100, chunk_overlap_tokens=10) == []

    def test_short_document_produces_a_single_chunk(self) -> None:
        chunks = chunk_document(
            _document("hello world this is a short document"),
            chunk_tokens=100,
            chunk_overlap_tokens=10,
        )
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert "hello" in chunks[0].content

    def test_long_document_produces_multiple_chunks(self) -> None:
        text = " ".join(f"word{i}" for i in range(500))
        chunks = chunk_document(_document(text), chunk_tokens=50, chunk_overlap_tokens=5)
        assert len(chunks) > 1

    def test_chunk_indices_are_sequential(self) -> None:
        text = " ".join(f"word{i}" for i in range(500))
        chunks = chunk_document(_document(text), chunk_tokens=50, chunk_overlap_tokens=5)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_consecutive_chunks_overlap(self) -> None:
        """Design §8.3: "modest overlap ... prevents a claim spanning a
        boundary from being lost by both chunks"."""
        text = " ".join(f"word{i}" for i in range(200))
        chunks = chunk_document(_document(text), chunk_tokens=30, chunk_overlap_tokens=10)
        assert len(chunks) >= 2

        first_words = chunks[0].content.split()
        second_words = chunks[1].content.split()
        overlap = set(first_words[-5:]) & set(second_words[:5])
        assert overlap, "expected the tail of chunk 0 to reappear in the head of chunk 1"

    def test_never_splits_a_word_across_chunks(self) -> None:
        text = " ".join(f"distinctive-word-{i}" for i in range(300))
        chunks = chunk_document(_document(text), chunk_tokens=40, chunk_overlap_tokens=8)
        all_words_in_original = set(text.split())
        for chunk in chunks:
            for word in chunk.content.split():
                assert word in all_words_in_original

    def test_source_ref_records_page_bounds(self) -> None:
        chunks = chunk_document(
            _document("page one content here", "page two content here"),
            chunk_tokens=3,
            chunk_overlap_tokens=1,
        )
        assert chunks
        for chunk in chunks:
            assert "page_start" in chunk.source_ref
            assert "page_end" in chunk.source_ref
            page_start = int(chunk.source_ref["page_start"])  # type: ignore[call-overload]
            page_end = int(chunk.source_ref["page_end"])  # type: ignore[call-overload]
            assert page_start <= page_end

    def test_source_ref_records_section_when_present(self) -> None:
        document = ExtractedDocument(
            pages=[
                ExtractedPage(page_number=1, text="intro text", section="Introduction"),
            ]
        )
        chunks = chunk_document(document, chunk_tokens=100, chunk_overlap_tokens=10)
        assert chunks[0].source_ref.get("section") == "Introduction"

    def test_source_ref_omits_section_when_absent(self) -> None:
        chunks = chunk_document(
            _document("plain text with no section"), chunk_tokens=100, chunk_overlap_tokens=10
        )
        assert "section" not in chunks[0].source_ref

    def test_chunk_spans_a_page_boundary_when_content_is_short(self) -> None:
        chunks = chunk_document(
            _document("short page one", "short page two"),
            chunk_tokens=100,
            chunk_overlap_tokens=5,
        )
        assert len(chunks) == 1
        assert chunks[0].source_ref["page_start"] == 1
        assert chunks[0].source_ref["page_end"] == 2

    def test_respects_the_configured_chunk_size_approximately(self) -> None:
        text = " ".join(f"word{i}" for i in range(1000))
        chunks = chunk_document(_document(text), chunk_tokens=100, chunk_overlap_tokens=0)
        # Every non-final chunk should be close to the token budget, not
        # trivially small (sanity check on the packing loop).
        assert all(len(chunk.content.split()) >= 50 for chunk in chunks[:-1])
