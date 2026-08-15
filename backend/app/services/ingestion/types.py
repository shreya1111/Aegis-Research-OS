"""Shared data structures for the ingestion pipeline (design §8.2, §8.3, §8.4)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """One page (or page-equivalent section) of extracted text.

    ``page_number`` is 1-indexed to match how citations are displayed to users
    (design: `[Doc 2, p.4]`). ``used_ocr`` and ``ocr_confidence`` are set only
    when this page went through the OCR fallback (design §8.2).
    """

    page_number: int
    text: str
    used_ocr: bool = False
    #: Tesseract's mean per-word confidence (0-100), or ``None`` when OCR was
    #: not used for this page.
    ocr_confidence: float | None = None
    #: Section/heading title if the parser could determine one (DOCX headings;
    #: best-effort for PDF). ``None`` when unavailable.
    section: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """The full result of parsing one uploaded file (design §8.2, §8.4)."""

    pages: list[ExtractedPage]
    #: Best-effort metadata (design §8.4). Never authoritative.
    title: str | None = None
    authors: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def used_ocr(self) -> bool:
        return any(page.used_ocr for page in self.pages)

    def min_ocr_confidence(self) -> float | None:
        """Lowest per-page OCR confidence across the document, or ``None`` if
        no page used OCR.

        The caller compares this against ``settings.ocr_confidence_threshold``
        to decide whether to flag the document (design §8.2 "the OCR honesty
        rule") — the threshold is configuration, not a property of the
        extraction result itself.
        """
        confidences = [
            page.ocr_confidence
            for page in self.pages
            if page.used_ocr and page.ocr_confidence is not None
        ]
        return min(confidences) if confidences else None

    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


@dataclass(frozen=True, slots=True)
class Chunk:
    """One token-aware slice of an :class:`ExtractedDocument`, ready to embed
    (design §8.3)."""

    chunk_index: int
    content: str
    source_ref: dict[str, object]
