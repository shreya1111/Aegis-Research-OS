"""Best-effort document metadata assembly (design §8.4).

Extraction is heuristic and may be wrong — the values here are stored in
``documents.metadata`` and presented as inspectable, not authoritative
(design §8.4).
"""

from __future__ import annotations

from typing import Any

from app.services.ingestion.types import ExtractedDocument


def build_metadata(
    extracted: ExtractedDocument,
    *,
    mime_type: str,
    size_bytes: int,
    ocr_confidence_threshold: float,
) -> dict[str, Any]:
    """Assemble the ``documents.metadata`` JSONB payload for a successful
    extraction (design §8.4 field list)."""
    min_confidence = extracted.min_ocr_confidence()
    ocr_low_confidence = min_confidence is not None and min_confidence < ocr_confidence_threshold

    return {
        "title": extracted.title,
        "authors": extracted.authors,
        "page_count": extracted.page_count,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "ocr_used": extracted.used_ocr,
        "ocr_low_confidence": ocr_low_confidence,
        "ocr_min_confidence": min_confidence,
        "failure_reason": None,
    }


def build_failure_metadata(
    *, mime_type: str, size_bytes: int, failure_reason: str
) -> dict[str, Any]:
    """Assemble ``documents.metadata`` for a failed extraction (design §8.1,
    §6.10: "recorded, not raised to the user")."""
    return {
        "title": None,
        "authors": [],
        "page_count": None,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "ocr_used": False,
        "ocr_low_confidence": False,
        "ocr_min_confidence": None,
        "failure_reason": failure_reason,
    }
