"""``documents`` table (design §7.2, FR-C).

One uploaded source file and its processing state through the
``pending → processing → ready | failed`` lifecycle (design §8.1).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.document_chunk import DocumentChunk


class DocumentStatus(StrEnum):
    """Ingestion lifecycle state (design §8.1, FR-C8)."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(UUIDPrimaryKeyMixin, Base):
    """An uploaded source file.

    ``uploaded_at`` stands in for this table's ``created_at`` (design §7.2
    names it explicitly), so this model does not use ``CreatedAtMixin``.
    """

    __tablename__ = "documents"
    __table_args__ = (
        # Serves the Documents tab listing (design §7.4).
        Index("ix_documents_project_id_uploaded_at", "project_id", "uploaded_at"),
        # Serves ingestion-status polling for in-flight documents (design §7.4):
        # a partial index would need a raw DDL predicate, which Alembic autogen
        # does not express portably — the plain composite index still serves
        # the "documents for this project, filtered by status" query well at
        # the scale this system targets.
        Index("ix_documents_project_id_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        String(20),
        nullable=False,
        default=DocumentStatus.PENDING,
    )
    #: Title, authors, page_count, mime_type, size_bytes, ocr_used,
    #: ocr_low_confidence, failure_reason — open-ended, so JSONB (design §8.4).
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentChunk.chunk_index",
    )
