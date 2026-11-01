"""``/projects/{id}/activity`` and ``/projects/{id}/usage`` (Phase 10, FR-H7, FR-H9).

Both read-only views are open to every member of the project: a viewer needs to
see what has happened in the workspace they were invited to, and neither view
exposes content beyond action labels and aggregate spend.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ActivityServiceDep, UsageServiceDep
from app.api.v1.deps import ProjectInScopeDep
from app.core.envelope import ok, paginated
from app.schemas.activity import ActivityRead
from app.schemas.common import ApiResponse, Page, PaginationParams
from app.schemas.usage import UsageRead

router = APIRouter(tags=["collaboration"])

PaginationQuery = Annotated[PaginationParams, Query()]


@router.get(
    "/projects/{project_id}/activity",
    response_model=ApiResponse[Page[ActivityRead]],
    summary="List the project's audit trail, newest first",
)
async def list_activity(
    project: ProjectInScopeDep,
    pagination: PaginationQuery,
    activity_service: ActivityServiceDep,
) -> ApiResponse[Page[ActivityRead]]:
    entries, total = await activity_service.list_for_project(
        project_id=project.id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginated(
        [ActivityRead.from_model(entry) for entry in entries],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/projects/{project_id}/usage",
    response_model=ApiResponse[UsageRead],
    summary="Token, cost, and run totals for the project",
)
async def get_usage(
    project: ProjectInScopeDep,
    usage_service: UsageServiceDep,
) -> ApiResponse[UsageRead]:
    summary = await usage_service.summary(project_id=project.id)
    return ok(UsageRead.from_summary(summary))
