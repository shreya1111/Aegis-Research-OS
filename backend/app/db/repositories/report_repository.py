"""Repository for report CRUD operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.report import Report, ReportStatus, ReportType


class ReportRepository:
    """Database operations for research artifact reports."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: UUID,
        type: ReportType,
        title: str,
    ) -> Report:
        """Create a new report in PENDING status."""
        report = Report(
            project_id=project_id,
            type=type,
            title=title,
            status=ReportStatus.PENDING,
        )
        self._session.add(report)
        await self._session.flush()
        return report

    async def get_by_id_for_project(self, report_id: UUID, project_id: UUID) -> Report | None:
        """Get a report by ID, scoped to a project."""
        stmt = select(Report).where(Report.id == report_id, Report.project_id == project_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_project(self, project_id: UUID) -> list[Report]:
        """List all reports for a project, ordered by creation time descending."""
        stmt = (
            select(Report)
            .where(Report.project_id == project_id)
            .order_by(Report.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, report: Report, status: ReportStatus) -> None:
        """Update a report's status."""
        report.status = status
        await self._session.flush()

    async def update_content(self, report: Report, content: str) -> None:
        """Update a report's generated content."""
        report.content_markdown = content
        report.status = ReportStatus.COMPLETED
        await self._session.flush()

    async def update_error(self, report: Report, error_message: str) -> None:
        """Mark a report as failed with an error message."""
        report.error_message = error_message
        report.status = ReportStatus.FAILED
        await self._session.flush()

    async def delete(self, report: Report) -> None:
        """Delete a report."""
        await self._session.delete(report)
        await self._session.flush()
