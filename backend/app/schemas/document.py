"""Wire contracts for document ingestion (design §6.1, FR-C)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.document import Document


class DocumentMetadata(BaseModel):
    """Best-effort extracted metadata (design §8.4).

    Presented as inspectable, not authoritative — every field may be ``None``.
    """

    model_config = ConfigDict(frozen=True)

    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    page_count: int | None = None
    mime_type: str
    size_bytes: int
    ocr_used: bool = False
    ocr_low_confidence: bool = False
    ocr_min_confidence: float | None = None
    failure_reason: str | None = None


class DocumentRead(BaseModel):
    """Document representation returned to the owner (design FR-C8)."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    project_id: UUID
    filename: str
    status: str
    metadata: DocumentMetadata
    uploaded_at: datetime

    @classmethod
    def from_model(cls, document: Document) -> DocumentRead:
        """Build from the ORM model, mapping its ``metadata_`` attribute
        (renamed to avoid colliding with SQLAlchemy's reserved ``metadata``)
        back onto the public ``metadata`` field name."""
        return cls(
            id=document.id,
            project_id=document.project_id,
            filename=document.filename,
            status=document.status,
            metadata=DocumentMetadata.model_validate(document.metadata_),
            uploaded_at=document.uploaded_at,
        )
