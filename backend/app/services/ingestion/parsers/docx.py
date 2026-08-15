"""DOCX parsing (design §8.2, FR-C3).

``python-docx`` exposes paragraphs and their styles, which lets heading
structure be preserved (design: "with heading structure retained") for use as
the ``section`` field in citation provenance. DOCX has no native page concept,
so the whole document is treated as a single logical page — chunking still
splits it into retrieval-sized pieces; only the citation label differs
(section title rather than a page number).
"""

from __future__ import annotations

import io

from docx import Document as DocxDocument
from docx.opc.exceptions import PackageNotFoundError

from app.services.ingestion.errors import ExtractionError
from app.services.ingestion.types import ExtractedDocument, ExtractedPage

#: python-docx style names used for Word's built-in heading styles.
_HEADING_STYLE_PREFIX = "Heading"


def _is_heading(style_name: str | None) -> bool:
    return style_name is not None and style_name.startswith(_HEADING_STYLE_PREFIX)


def parse_docx(content: bytes) -> ExtractedDocument:
    """Extract text and heading structure from a DOCX file.

    Raises
    ------
    ExtractionError
        If the file is not a valid DOCX package (design: "recorded, not raised
        to the user" — caught by the pipeline and marked failed).
    """
    try:
        document = DocxDocument(io.BytesIO(content))
    except PackageNotFoundError as exc:
        raise ExtractionError(
            "This file could not be read as a DOCX document. It may be corrupted "
            "or in an unsupported format."
        ) from exc
    except Exception as exc:
        raise ExtractionError("This DOCX document could not be read.") from exc

    core_properties = document.core_properties
    title = core_properties.title or None
    authors = [core_properties.author] if core_properties.author else []

    pages: list[ExtractedPage] = []
    current_section: str | None = None
    buffer: list[str] = []
    page_number = 1

    def flush() -> None:
        nonlocal buffer, page_number
        text = "\n".join(buffer).strip()
        if text:
            pages.append(ExtractedPage(page_number=page_number, text=text, section=current_section))
            page_number += 1
        buffer = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        if _is_heading(paragraph.style.name if paragraph.style else None):
            flush()
            current_section = text
            buffer.append(text)
        else:
            buffer.append(text)

    flush()

    if not pages:
        raise ExtractionError("This DOCX document has no readable text content.")

    return ExtractedDocument(pages=pages, title=title, authors=authors)
