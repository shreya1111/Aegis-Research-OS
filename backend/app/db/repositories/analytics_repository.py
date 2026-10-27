"""Repository for analytics datasets and analyses (Phase 8)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analytics import AnalyticsAnalysis, AnalyticsDataset


class AnalyticsRepository:
    """Data access for analytics datasets and analyses."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_dataset(
        self,
        *,
        project_id: UUID,
        filename: str,
        file_path: str,
    ) -> AnalyticsDataset:
        """Create a new analytics dataset record."""
        dataset = AnalyticsDataset(
            project_id=project_id,
            filename=filename,
            file_path=file_path,
            status="pending",
        )
        self._session.add(dataset)
        await self._session.flush()
        return dataset

    async def get_dataset(
        self, dataset_id: UUID, *, project_id: UUID | None = None
    ) -> AnalyticsDataset | None:
        """Get dataset by ID, optionally scoped to a project."""
        stmt = select(AnalyticsDataset).where(AnalyticsDataset.id == dataset_id)
        if project_id is not None:
            stmt = stmt.where(AnalyticsDataset.project_id == project_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_dataset_required(self, dataset_id: UUID) -> AnalyticsDataset:
        """Internal method to get dataset, expecting it to exist."""
        result = await self._session.execute(
            select(AnalyticsDataset).where(AnalyticsDataset.id == dataset_id)
        )
        return result.scalar_one()

    async def list_datasets(self, project_id: UUID) -> list[AnalyticsDataset]:
        """List all datasets in a project."""
        stmt = (
            select(AnalyticsDataset)
            .where(AnalyticsDataset.project_id == project_id)
            .order_by(AnalyticsDataset.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_dataset_profile(
        self,
        dataset_id: UUID,
        *,
        row_count: int,
        column_count: int,
        profile_data: dict,
    ) -> AnalyticsDataset:
        """Update dataset profiling information."""
        dataset = await self._get_dataset_required(dataset_id)
        dataset.row_count = row_count
        dataset.column_count = column_count
        dataset.profile_data = profile_data
        dataset.status = "profiled"
        await self._session.flush()
        return dataset

    async def mark_dataset_failed(
        self, dataset_id: UUID, error: str
    ) -> AnalyticsDataset:
        """Mark a dataset as failed."""
        dataset = await self._get_dataset_required(dataset_id)
        dataset.status = "failed"
        # Store error in profile_data
        dataset.profile_data = {"error": error}
        await self._session.flush()
        return dataset

    async def create_analysis(
        self,
        *,
        dataset_id: UUID,
        project_id: UUID,
        question: str,
    ) -> AnalyticsAnalysis:
        """Create a new analysis request."""
        analysis = AnalyticsAnalysis(
            dataset_id=dataset_id,
            project_id=project_id,
            question=question,
            status="pending",
        )
        self._session.add(analysis)
        await self._session.flush()
        return analysis

    async def get_analysis(
        self, analysis_id: UUID, *, project_id: UUID | None = None
    ) -> AnalyticsAnalysis | None:
        """Get analysis by ID, optionally scoped to a project."""
        stmt = select(AnalyticsAnalysis).where(AnalyticsAnalysis.id == analysis_id)
        if project_id is not None:
            stmt = stmt.where(AnalyticsAnalysis.project_id == project_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_analysis_required(self, analysis_id: UUID) -> AnalyticsAnalysis:
        """Internal method to get analysis, expecting it to exist."""
        result = await self._session.execute(
            select(AnalyticsAnalysis).where(AnalyticsAnalysis.id == analysis_id)
        )
        return result.scalar_one()

    async def list_analyses(self, dataset_id: UUID) -> list[AnalyticsAnalysis]:
        """List all analyses for a dataset."""
        stmt = (
            select(AnalyticsAnalysis)
            .where(AnalyticsAnalysis.dataset_id == dataset_id)
            .order_by(AnalyticsAnalysis.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_analysis_result(
        self,
        analysis_id: UUID,
        *,
        analysis_code: str,
        result_data: dict,
        chart_data: dict | None,
        explanation: str,
    ) -> AnalyticsAnalysis:
        """Update analysis with results."""
        analysis = await self._get_analysis_required(analysis_id)
        analysis.analysis_code = analysis_code
        analysis.result_data = result_data
        analysis.chart_data = chart_data
        analysis.explanation = explanation
        analysis.status = "completed"
        await self._session.flush()
        return analysis

    async def mark_analysis_failed(
        self, analysis_id: UUID, error: str
    ) -> AnalyticsAnalysis:
        """Mark an analysis as failed."""
        analysis = await self._get_analysis_required(analysis_id)
        analysis.status = "failed"
        analysis.error_message = error
        await self._session.flush()
        return analysis

    async def delete_dataset(self, dataset_id: UUID, *, project_id: UUID) -> None:
        """Delete a dataset and all its analyses."""
        dataset = await self._get_dataset_required(dataset_id)
        if dataset.project_id != project_id:
            raise ValueError("Dataset does not belong to the specified project")
        await self._session.delete(dataset)
        await self._session.flush()
