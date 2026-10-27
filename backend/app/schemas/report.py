"""Report request/response schemas for Phase 6 research artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.report import ReportStatus, ReportType

if TYPE_CHECKING:
    from app.db.models.report import Report


class ReportCreate(BaseModel):
    """Request to generate a new research artifact."""

    type: ReportType = Field(..., description="Type of research artifact to generate")
    title: str = Field(..., min_length=1, max_length=500, description="Title for the report")


class ReportRead(BaseModel):
    """Response schema for a report."""

    id: UUID
    project_id: UUID
    type: ReportType
    status: ReportStatus
    title: str
    content_markdown: str | None = None
    error_message: str | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, report: Report) -> ReportRead:
        """Convert from SQLAlchemy model."""

        return cls(
            id=report.id,
            project_id=report.project_id,
            type=report.type,
            status=report.status,
            title=report.title,
            content_markdown=report.content_markdown,
            error_message=report.error_message,
            created_at=report.created_at,
        )
