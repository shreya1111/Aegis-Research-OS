"""``document_chunks`` table (design §7.2, §4.4, FR-C6, FR-C7).

The retrieval unit: carries the embedding and the citation provenance
(``source_ref``) needed to make ``[Doc 2, p.4]`` verifiable rather than
decorative (design §8.3).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.document import Document


class DocumentChunk(UUIDPrimaryKeyMixin, Base):
    """One retrieval-sized slice of a document, with its embedding and
    citation provenance.

    ``project_id`` is denormalised from ``document_id`` (design §7.2, §7.5) so
    project-scoped vector and full-text search filter without a join — the
    hottest query path in the system.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        # Ordered reconstruction and citation resolution (design §7.4).
        Index("ix_document_chunks_document_id_chunk_index", "document_id", "chunk_index"),
        # Tenancy scope filter on the hot retrieval path (design §7.4, §7.5).
        Index("ix_document_chunks_project_id", "project_id"),
        # Keyword half of hybrid retrieval (design §7.4, §8.6). GIN over the
        # generated tsvector column defined below.
        Index("ix_document_chunks_content_tsv", "content_tsv", postgresql_using="gin"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Denormalised from `documents.project_id` — see class docstring.
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    #: Dimensionality fixed by `settings.embedding_dimensions` (design §4.3);
    #: read once at import time since the column type is a migration-time
    #: decision, not a per-request one.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(get_settings().embedding_dimensions),
        nullable=True,
    )
    #: Page number, section heading, char offsets (design §8.3) — the basis of
    #: citation markers like `[Doc 2, p.4]`.
    source_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    #: Generated column: Postgres maintains this automatically from `content`
    #: (design §7.2: "a generated tsvector column"). Never written by the ORM.
    content_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
        nullable=False,
    )

    document: Mapped[Document] = relationship(back_populates="chunks")
