"""Analytics API endpoints for Phase 8."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.api.deps import (
    CurrentUserDep,
    DbSessionDep,
    LLMProviderDep,
    MembershipServiceDep,
    ProjectServiceDep,
    SettingsDep,
)
from app.api.v1.deps import ProjectEditorDep, ProjectInScopeDep, resolve_project_access
from app.core.config import get_settings
from app.core.envelope import ok
from app.core.errors import FileTooLargeError, NotFoundError, PermissionDeniedError
from app.db.models.analytics import AnalyticsDataset
from app.db.models.project_member import ProjectRole
from app.db.models.user import User
from app.db.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsAnalysisCreate,
    AnalyticsAnalysisRead,
    AnalyticsDatasetRead,
)
from app.schemas.common import ApiResponse
from app.services.analytics_service import AnalyticsService
from app.services.ingestion.validation import sanitise_filename
from app.services.membership_service import MembershipService
from app.services.project_service import ProjectService

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


async def _authorised_dataset(
    dataset_id: UUID,
    *,
    repo: AnalyticsRepository,
    current_user: User,
    project_service: ProjectService,
    membership_service: MembershipService,
    minimum: ProjectRole = ProjectRole.VIEWER,
) -> AnalyticsDataset:
    """Load a dataset and authorise the caller through its project.

    Dataset-scoped routes cannot use the ``{project_id}`` dependency because the
    path carries the dataset id only. Authorising here — through the dataset's
    own ``project_id`` — keeps membership rules in one place and makes a foreign
    dataset indistinguishable from a missing one (design §9.3 rule 4).
    """
    dataset = await repo.get_dataset(dataset_id)
    if dataset is None:
        raise NotFoundError("Dataset not found.")

    context = await resolve_project_access(
        dataset.project_id,
        user_id=current_user.id,
        project_service=project_service,
        membership_service=membership_service,
    )
    if not context.role.at_least(minimum):
        raise PermissionDeniedError(
            f"This action requires the {minimum.value} role on this project."
        )
    return dataset


@router.post(
    "/projects/{project_id}/analytics/datasets",
    response_model=ApiResponse[AnalyticsDatasetRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV dataset for analysis",
)
async def upload_dataset(
    project: ProjectEditorDep,
    background_tasks: BackgroundTasks,
    session: DbSessionDep,
    repo: AnalyticsRepositoryDep,
    analytics_service: AnalyticsServiceDep,
    settings: SettingsDep,
    file: UploadedFile,
) -> ApiResponse[AnalyticsDatasetRead]:
    """Upload a CSV file for analysis."""
    # Validate file type. Browsers may report a mixed-case extension, and the
    # filename also ends up in the UI, so strip any directory component.
    filename = sanitise_filename(file.filename or "")
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )

    # Read at most one byte past the limit: an oversized upload is detected
    # without buffering the whole file in memory first (design §9.5).
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        max_mb = settings.max_upload_bytes // (1024 * 1024)
        raise FileTooLargeError(f"Files must be {max_mb} MB or smaller.")
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
        filename=filename,
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
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[AnalyticsDatasetRead]:
    """Get dataset details including profile."""
    dataset = await _authorised_dataset(
        dataset_id,
        repo=repo,
        current_user=current_user,
        project_service=project_service,
        membership_service=membership_service,
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
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[AnalyticsAnalysisRead]:
    """Ask a natural-language question about the dataset."""
    dataset = await _authorised_dataset(
        dataset_id,
        repo=repo,
        current_user=current_user,
        project_service=project_service,
        membership_service=membership_service,
        minimum=ProjectRole.EDITOR,
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
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[list[AnalyticsAnalysisRead]]:
    """List all analyses for a dataset."""
    await _authorised_dataset(
        dataset_id,
        repo=repo,
        current_user=current_user,
        project_service=project_service,
        membership_service=membership_service,
    )
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
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[AnalyticsAnalysisRead]:
    """Get analysis results including code, data, and explanation."""
    analysis = await repo.get_analysis(analysis_id)
    if analysis is None:
        raise NotFoundError("Analysis not found.")
    await resolve_project_access(
        analysis.project_id,
        user_id=current_user.id,
        project_service=project_service,
        membership_service=membership_service,
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
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[None]:
    """Delete a dataset and all its analyses."""
    dataset = await _authorised_dataset(
        dataset_id,
        repo=repo,
        current_user=current_user,
        project_service=project_service,
        membership_service=membership_service,
        minimum=ProjectRole.EDITOR,
    )
    await repo.delete_dataset(dataset_id, project_id=dataset.project_id)

    # Delete file
    try:
        Path(dataset.file_path).unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"Failed to delete dataset file: {e}")

    return ok(None)
