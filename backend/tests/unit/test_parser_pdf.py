"""Unit tests for PDF parsing with OCR fallback (design §8.2, FR-C3, FR-C4).

Real PDFs are generated on the fly with PyMuPDF: a digital page (real text
layer) and a "scanned" page (text rasterised into an image, no text layer) to
exercise the OCR path end to end against the installed Tesseract binary.
"""

from __future__ import annotations

import io
import shutil

import fitz
import pytest
from PIL import Image, ImageDraw

from app.services.ingestion.errors import ExtractionError
from app.services.ingestion.parsers.pdf import parse_pdf

#: The OCR path shells out to the Tesseract binary, which is installed in
#: ``deployment/Dockerfile.backend`` but is not guaranteed on a bare host.
requires_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="Tesseract OCR binary is not installed on this machine",
)


def _digital_pdf_bytes(*, pages: list[str], title: str | None = None) -> bytes:
    doc = fitz.open()
    if title:
        doc.set_metadata({"title": title})
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=14)
    data = bytes(doc.tobytes())
    doc.close()
    return data


def _scanned_pdf_bytes(text: str) -> bytes:
    """Build a one-page PDF whose page is an image with no text layer, so
    extractable text is empty and the OCR fallback triggers (design §8.2
    detection heuristic)."""
    image = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 80), text, fill="black")

    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    doc = fitz.open()
    page = doc.new_page(width=800, height=200)
    page.insert_image(fitz.Rect(0, 0, 800, 200), stream=image_bytes.getvalue())
    data = bytes(doc.tobytes())
    doc.close()
    return data


@pytest.mark.unit
class TestParsePdf:
    def test_extracts_digital_text(self) -> None:
        pdf = _digital_pdf_bytes(pages=["Hello World Test Document"])
        extracted = parse_pdf(pdf, ocr_enabled=True, ocr_trigger_char_threshold=20)
        assert "Hello World Test Document" in extracted.full_text()

    def test_digital_pages_do_not_use_ocr(self) -> None:
        pdf = _digital_pdf_bytes(pages=["Some perfectly normal digital text content here"])
        extracted = parse_pdf(pdf, ocr_enabled=True, ocr_trigger_char_threshold=20)
        assert extracted.used_ocr is False

    def test_page_numbers_are_one_indexed_and_sequential(self) -> None:
        pdf = _digital_pdf_bytes(pages=["Page one content here", "Page two content here"])
        extracted = parse_pdf(pdf, ocr_enabled=True, ocr_trigger_char_threshold=20)
        assert [page.page_number for page in extracted.pages] == [1, 2]

    def test_extracts_title_metadata_when_present(self) -> None:
        pdf = _digital_pdf_bytes(pages=["Some content here for the document"], title="My Paper")
        extracted = parse_pdf(pdf, ocr_enabled=True, ocr_trigger_char_threshold=20)
        assert extracted.title == "My Paper"

    @requires_tesseract
    def test_scanned_page_falls_back_to_ocr(self) -> None:
        pdf = _scanned_pdf_bytes("SCANNED DOCUMENT TEXT")
        extracted = parse_pdf(pdf, ocr_enabled=True, ocr_trigger_char_threshold=20)
        assert extracted.used_ocr is True
        assert extracted.pages[0].ocr_confidence is not None

    @requires_tesseract
    def test_ocr_recovers_recognisable_text(self) -> None:
        pdf = _scanned_pdf_bytes("HELLO OCR WORLD")
        extracted = parse_pdf(pdf, ocr_enabled=True, ocr_trigger_char_threshold=20)
        # OCR is not perfectly deterministic across environments; assert on a
        # substring rather than exact equality.
        assert "OCR" in extracted.full_text().upper()

    def test_ocr_disabled_keeps_sparse_digital_text_without_ocr(self) -> None:
        pdf = _scanned_pdf_bytes("SHOULD NOT BE OCRD")
        extracted = parse_pdf(pdf, ocr_enabled=False, ocr_trigger_char_threshold=20)
        assert extracted.used_ocr is False

    def test_raises_extraction_error_for_a_corrupt_file(self) -> None:
        with pytest.raises(ExtractionError):
            parse_pdf(b"not a pdf at all", ocr_enabled=True, ocr_trigger_char_threshold=20)

    def test_raises_extraction_error_for_empty_bytes(self) -> None:
        with pytest.raises(ExtractionError):
            parse_pdf(b"", ocr_enabled=True, ocr_trigger_char_threshold=20)
