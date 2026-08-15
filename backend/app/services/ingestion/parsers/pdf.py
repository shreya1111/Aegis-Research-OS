"""PDF parsing with OCR fallback (design §8.2, FR-C3, FR-C4).

Digital PDFs are parsed with ``pdfplumber`` (good layout/page fidelity). Pages
with negligible extractable text are treated as scanned and rasterised with
PyMuPDF, then OCR'd with ``pytesseract`` — this avoids a dependency on the
poppler system binary that ``pdf2image`` would otherwise require, keeping the
Docker image smaller and the local dev setup simpler.
"""

from __future__ import annotations

import io
from typing import Any

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image

from app.core.logging import get_logger
from app.services.ingestion.errors import ExtractionError
from app.services.ingestion.types import ExtractedDocument, ExtractedPage

logger = get_logger(__name__)

#: PyMuPDF render resolution for OCR rasterisation. 300 DPI is the commonly
#: recommended floor for Tesseract accuracy on standard document text.
_OCR_RENDER_DPI = 300


def _extract_pdf_metadata(pdf: Any) -> tuple[str | None, list[str]]:
    """Best-effort title/authors from PDF document metadata (design §8.4)."""
    info = pdf.metadata or {}
    title = info.get("Title") or None
    author_field = info.get("Author") or ""
    authors = [name.strip() for name in author_field.split(";") if name.strip()]
    return title, authors


def _ocr_page(pdf_bytes: bytes, page_index: int) -> tuple[str, float]:
    """Rasterise one page and OCR it, returning text and mean confidence.

    ``page_index`` is 0-indexed, matching both PyMuPDF and pdfplumber.
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        page = doc[page_index]
        zoom = _OCR_RENDER_DPI / 72  # PDF points are 72 DPI native.
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))

    ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    text = pytesseract.image_to_string(image)

    confidences = [float(c) for c in ocr_data.get("conf", []) if c not in ("-1", -1)]
    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return text, mean_confidence


def parse_pdf(
    content: bytes,
    *,
    ocr_enabled: bool,
    ocr_trigger_char_threshold: int,
) -> ExtractedDocument:
    """Extract text, page structure, and best-effort metadata from a PDF.

    Pages whose extractable text is shorter than ``ocr_trigger_char_threshold``
    characters are treated as scanned and OCR'd instead, when ``ocr_enabled``
    (design §8.2 detection heuristic).

    Raises
    ------
    ExtractionError
        If the file cannot be opened as a PDF at all (design: "recorded, not
        raised to the user" — the pipeline catches this and marks the document
        failed).
    """
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            title, authors = _extract_pdf_metadata(pdf)
            digital_pages = [(page.page_number, page.extract_text() or "") for page in pdf.pages]
    except Exception as exc:
        raise ExtractionError(
            "This file could not be read as a PDF. It may be corrupted or password-protected."
        ) from exc

    if not digital_pages:
        raise ExtractionError("This PDF has no pages.")

    pages: list[ExtractedPage] = []
    for page_number, text in digital_pages:
        needs_ocr = len(text.strip()) < ocr_trigger_char_threshold

        if needs_ocr and ocr_enabled:
            try:
                ocr_text, confidence = _ocr_page(content, page_number - 1)
                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=ocr_text,
                        used_ocr=True,
                        ocr_confidence=confidence,
                    )
                )
                continue
            except Exception:
                logger.warning(
                    "ingestion.ocr_page_failed",
                    extra={"event": "ingestion.ocr_page_failed", "page_number": page_number},
                )
                # Fall through and keep whatever digital text was extracted,
                # even if sparse — better than losing the page entirely.

        pages.append(ExtractedPage(page_number=page_number, text=text))

    return ExtractedDocument(pages=pages, title=title, authors=authors)
