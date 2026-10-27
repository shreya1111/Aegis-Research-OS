"""Pydantic schemas for analytics datasets and analyses (Phase 8)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AnalyticsDatasetBase(BaseModel):
    """Base schema for analytics datasets."""

    filename: str


class AnalyticsDatasetCreate(AnalyticsDatasetBase):
    """Schema for creating an analytics dataset."""

    pass


class AnalyticsDatasetRead(AnalyticsDatasetBase):
    """Schema for reading an analytics dataset."""

    id: UUID
    project_id: UUID
    status: str
    row_count: int | None = None
    column_count: int | None = None
    profile_data: dict[str, Any] | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, dataset: Any) -> AnalyticsDatasetRead:
        return cls(
            id=dataset.id,
            project_id=dataset.project_id,
            filename=dataset.filename,
            status=dataset.status,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            profile_data=dataset.profile_data,
            created_at=dataset.created_at,
        )


class AnalyticsAnalysisCreate(BaseModel):
    """Schema for creating an analysis request."""

    question: str = Field(..., min_length=1, max_length=5000)


class AnalyticsAnalysisRead(BaseModel):
    """Schema for reading an analysis result."""

    id: UUID
    dataset_id: UUID
    project_id: UUID
    question: str
    analysis_code: str | None = None
    result_data: dict[str, Any] | None = None
    chart_data: dict[str, Any] | None = None
    explanation: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, analysis: Any) -> AnalyticsAnalysisRead:
        return cls(
            id=analysis.id,
            dataset_id=analysis.dataset_id,
            project_id=analysis.project_id,
            question=analysis.question,
            analysis_code=analysis.analysis_code,
            result_data=analysis.result_data,
            chart_data=analysis.chart_data,
            explanation=analysis.explanation,
            status=analysis.status,
            error_message=analysis.error_message,
            created_at=analysis.created_at,
        )
