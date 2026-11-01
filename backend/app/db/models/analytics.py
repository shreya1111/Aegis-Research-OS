"""Analytics dataset and analysis models for Phase 8."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.project import Project


class AnalyticsDataset(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """CSV dataset uploaded for analysis."""

    __tablename__ = "analytics_datasets"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20))  # pending, profiled, failed
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    file_path: Mapped[str] = mapped_column(String(1000))

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="analytics_datasets")  # type: ignore
    analyses: Mapped[list["AnalyticsAnalysis"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class AnalyticsAnalysis(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """AI-assisted analysis of a dataset."""

    __tablename__ = "analytics_analyses"

    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("analytics_datasets.id", ondelete="CASCADE")
    )
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    analysis_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    chart_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # pending, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    dataset: Mapped["AnalyticsDataset"] = relationship(back_populates="analyses")
    project: Mapped["Project"] = relationship()  # type: ignore
