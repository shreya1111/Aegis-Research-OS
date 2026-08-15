"""Unit tests for best-effort metadata assembly (design §8.4)."""

from __future__ import annotations

import pytest

from app.services.ingestion.metadata import build_failure_metadata, build_metadata
from app.services.ingestion.types import ExtractedDocument, ExtractedPage


@pytest.mark.unit
class TestBuildMetadata:
    def test_includes_title_and_authors(self) -> None:
        extracted = ExtractedDocument(
            pages=[ExtractedPage(page_number=1, text="content")],
            title="My Paper",
            authors=["Ada Lovelace"],
        )
        metadata = build_metadata(
            extracted, mime_type="application/pdf", size_bytes=100, ocr_confidence_threshold=60.0
        )
        assert metadata["title"] == "My Paper"
        assert metadata["authors"] == ["Ada Lovelace"]

    def test_includes_page_count(self) -> None:
        extracted = ExtractedDocument(
            pages=[
                ExtractedPage(page_number=1, text="a"),
                ExtractedPage(page_number=2, text="b"),
            ]
        )
        metadata = build_metadata(
            extracted, mime_type="application/pdf", size_bytes=100, ocr_confidence_threshold=60.0
        )
        assert metadata["page_count"] == 2

    def test_ocr_used_is_false_when_no_page_used_ocr(self) -> None:
        extracted = ExtractedDocument(pages=[ExtractedPage(page_number=1, text="a")])
        metadata = build_metadata(
            extracted, mime_type="application/pdf", size_bytes=100, ocr_confidence_threshold=60.0
        )
        assert metadata["ocr_used"] is False
        assert metadata["ocr_low_confidence"] is False

    def test_flags_low_confidence_ocr(self) -> None:
        extracted = ExtractedDocument(
            pages=[
                ExtractedPage(page_number=1, text="a", used_ocr=True, ocr_confidence=30.0),
            ]
        )
        metadata = build_metadata(
            extracted, mime_type="application/pdf", size_bytes=100, ocr_confidence_threshold=60.0
        )
        assert metadata["ocr_used"] is True
        assert metadata["ocr_low_confidence"] is True
        assert metadata["ocr_min_confidence"] == 30.0

    def test_does_not_flag_high_confidence_ocr(self) -> None:
        extracted = ExtractedDocument(
            pages=[
                ExtractedPage(page_number=1, text="a", used_ocr=True, ocr_confidence=95.0),
            ]
        )
        metadata = build_metadata(
            extracted, mime_type="application/pdf", size_bytes=100, ocr_confidence_threshold=60.0
        )
        assert metadata["ocr_low_confidence"] is False

    def test_uses_the_lowest_confidence_across_pages(self) -> None:
        extracted = ExtractedDocument(
            pages=[
                ExtractedPage(page_number=1, text="a", used_ocr=True, ocr_confidence=95.0),
                ExtractedPage(page_number=2, text="b", used_ocr=True, ocr_confidence=40.0),
            ]
        )
        metadata = build_metadata(
            extracted, mime_type="application/pdf", size_bytes=100, ocr_confidence_threshold=60.0
        )
        assert metadata["ocr_min_confidence"] == 40.0
        assert metadata["ocr_low_confidence"] is True

    def test_failure_reason_is_none_on_success(self) -> None:
        extracted = ExtractedDocument(pages=[ExtractedPage(page_number=1, text="a")])
        metadata = build_metadata(
            extracted, mime_type="application/pdf", size_bytes=100, ocr_confidence_threshold=60.0
        )
        assert metadata["failure_reason"] is None


@pytest.mark.unit
class TestBuildFailureMetadata:
    def test_records_the_failure_reason(self) -> None:
        metadata = build_failure_metadata(
            mime_type="application/pdf", size_bytes=100, failure_reason="Corrupt file."
        )
        assert metadata["failure_reason"] == "Corrupt file."

    def test_all_extraction_fields_are_empty_or_none(self) -> None:
        metadata = build_failure_metadata(
            mime_type="application/pdf", size_bytes=100, failure_reason="Corrupt file."
        )
        assert metadata["title"] is None
        assert metadata["authors"] == []
        assert metadata["page_count"] is None
        assert metadata["ocr_used"] is False
