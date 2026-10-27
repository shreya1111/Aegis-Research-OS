"""Analytics API endpoints for Phase 8."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUserDep, DbSessionDep, LLMProviderDep
from app.api.v1.deps import ProjectInScopeDep
from app.core.config import get_settings
from app.core.envelope import ok
from app.core.llm.registry import get_llm_provider
from app.db.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsAnalysisCreate,
    AnalyticsAnalysisRead,
    AnalyticsDatasetRead,
)
from app.schemas.common import ApiResponse
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])

UploadedFile = Annotated[UploadFile, File(...)]

# Storage directory for uploaded datasets - lazy initialization
_STORAGE_DIR: Path | None = None


def get_storage_dir() -> Path:
    """Get or create storage directory."""
    global _STORAGE_DIR
    if _STORAGE_DIR is None:
        settings = get_settings()
        _STORAGE_DIR = Path(settings.data_dir) / "analytics"
        _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return _STORAGE_DIR


def get_analytics_repo(session: DbSessionDep) -> AnalyticsRepository:
    """Dependency for analytics repository."""
    return AnalyticsRepository(session)


def get_analytics_service(
    repo: Annotated[AnalyticsRepository, Depends(get_analytics_repo)],
    llm_provider: LLMProviderDep,
) -> AnalyticsService:
    """Dependency for analytics service."""
    return AnalyticsService(repository=repo, llm_provider=llm_provider)


AnalyticsRepositoryDep = Annotated[AnalyticsRepository, Depends(get_analytics_repo)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.post(
    "/projects/{project_id}/analytics/datasets",
    response_model=ApiResponse[AnalyticsDatasetRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV dataset for analysis",
)
async def upload_dataset(
    project: ProjectInScopeDep,
    background_tasks: BackgroundTasks,
    session: DbSessionDep,
    repo: AnalyticsRepositoryDep,
    analytics_service: AnalyticsServiceDep,
    file: UploadedFile,
) -> ApiResponse[AnalyticsDatasetRead]:
    """Upload a CSV file for analysis."""
    # Validate file type
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )

    # Read content
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file"
        )

    # Save file
    file_id = uuid4()
    file_path = get_storage_dir() / f"{file_id}.csv"
    file_path.write_bytes(content)

    # Create dataset record
    dataset = await repo.create_dataset(
        project_id=project.id,
        filename=file.filename,
        file_path=str(file_path),
    )

    # Commit before background task
    await session.commit()

    # Profile dataset in background
    background_tasks.add_task(
        analytics_service.profile_dataset,
        dataset.id,
        content,
    )

    return ok(AnalyticsDatasetRead.from_model(dataset))


@router.get(
    "/projects/{project_id}/analytics/datasets",
    response_model=ApiResponse[list[AnalyticsDatasetRead]],
    summary="List datasets in a project",
)
async def list_datasets(
    project: ProjectInScopeDep,
    repo: AnalyticsRepositoryDep,
) -> ApiResponse[list[AnalyticsDatasetRead]]:
    """List all analytics datasets in the project."""
    datasets = await repo.list_datasets(project.id)
    return ok([AnalyticsDatasetRead.from_model(d) for d in datasets])


@router.get(
    "/analytics/datasets/{dataset_id}",
    response_model=ApiResponse[AnalyticsDatasetRead],
    summary="Get dataset details",
)
async def get_dataset(
    dataset_id: UUID,
    current_user: CurrentUserDep,
    repo: AnalyticsRepositoryDep,
) -> ApiResponse[AnalyticsDatasetRead]:
    """Get dataset details including profile."""
    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    return ok(AnalyticsDatasetRead.from_model(dataset))


@router.post(
    "/analytics/datasets/{dataset_id}/analyze",
    response_model=ApiResponse[AnalyticsAnalysisRead],
    status_code=status.HTTP_201_CREATED,
    summary="Analyze dataset with AI",
)
async def analyze_dataset(
    dataset_id: UUID,
    request: AnalyticsAnalysisCreate,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
    session: DbSessionDep,
    repo: AnalyticsRepositoryDep,
    analytics_service: AnalyticsServiceDep,
) -> ApiResponse[AnalyticsAnalysisRead]:
    """Ask a natural-language question about the dataset."""
    # Get dataset
    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )

    # Create analysis record
    analysis = await repo.create_analysis(
        dataset_id=dataset_id,
        project_id=dataset.project_id,
        question=request.question,
    )

    # Commit before background task
    await session.commit()

    # Run analysis in background
    csv_content = Path(dataset.file_path).read_bytes()
    background_tasks.add_task(
        analytics_service.analyze_dataset,
        analysis.id,
        dataset_id,
        request.question,
        csv_content,
        dataset.profile_data or {},
    )

    return ok(AnalyticsAnalysisRead.from_model(analysis))


@router.get(
    "/analytics/datasets/{dataset_id}/analyses",
    response_model=ApiResponse[list[AnalyticsAnalysisRead]],
    summary="List analyses for a dataset",
)
async def list_analyses(
    dataset_id: UUID,
    current_user: CurrentUserDep,
    repo: AnalyticsRepositoryDep,
) -> ApiResponse[list[AnalyticsAnalysisRead]]:
    """List all analyses for a dataset."""
    analyses = await repo.list_analyses(dataset_id)
    return ok([AnalyticsAnalysisRead.from_model(a) for a in analyses])


@router.get(
    "/analytics/analyses/{analysis_id}",
    response_model=ApiResponse[AnalyticsAnalysisRead],
    summary="Get analysis results",
)
async def get_analysis(
    analysis_id: UUID,
    current_user: CurrentUserDep,
    repo: AnalyticsRepositoryDep,
) -> ApiResponse[AnalyticsAnalysisRead]:
    """Get analysis results including code, data, and explanation."""
    analysis = await repo.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    return ok(AnalyticsAnalysisRead.from_model(analysis))


@router.delete(
    "/analytics/datasets/{dataset_id}",
    response_model=ApiResponse[None],
    summary="Delete a dataset",
)
async def delete_dataset(
    dataset_id: UUID,
    current_user: CurrentUserDep,
    repo: AnalyticsRepositoryDep,
) -> ApiResponse[None]:
    """Delete a dataset and all its analyses."""
    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    await repo.delete_dataset(dataset_id, project_id=dataset.project_id)
    
    # Delete file
    try:
        Path(dataset.file_path).unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"Failed to delete dataset file: {e}")
    
    return ok(None)
