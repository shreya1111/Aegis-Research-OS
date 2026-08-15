"""Ingestion-specific exceptions (design §6.10).

``ExtractionError`` is deliberately never raised to the API layer — it is
caught by the pipeline and recorded as ``documents.status = failed`` with a
human-readable reason (design: "recorded, not raised to the user").
"""

from __future__ import annotations


class ExtractionError(Exception):
    """Text could not be extracted from the uploaded file.

    Carries a message safe to store in ``documents.metadata.failure_reason``
    and show to the user (design §6.10 principle 4: errors are actionable).
    """
