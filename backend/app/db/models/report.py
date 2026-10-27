"""Report model for generated research artifacts (design §8.10, Phase 6)."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.project import Project


class ReportType(str, Enum):
    """Types of research artifacts that can be generated."""

    LITERATURE_REVIEW = "literature_review"
    GAP_ANALYSIS = "gap_analysis"
    SOURCE_COMPARISON = "source_comparison"
    SURVEY = "survey"


class ReportStatus(str, Enum):
    """Generation status of a research artifact."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A generated research artifact (literature review, survey, etc.)."""

    __tablename__ = "reports"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ReportType] = mapped_column(String(50), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        String(20), nullable=False, default=ReportStatus.PENDING
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_markdown: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relationship to project
    project: Mapped[Project] = relationship("Project", back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report {self.id} ({self.type}, {self.status})>"
