"""``/projects`` router: CRUD for research workspaces (design §6.5, FR-B)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, ProjectServiceDep
from app.api.v1.deps import ProjectInScopeDep
from app.core.envelope import ok, paginated
from app.schemas.common import ApiResponse, Page, PaginationParams
from app.schemas.project import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])

#: Pydantic model bound to query parameters, not the request body — required
#: for a GET route (design §6.1 pagination convention).
PaginationQuery = Annotated[PaginationParams, Query()]


@router.post(
    "",
    response_model=ApiResponse[ProjectRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a research workspace",
)
async def create_project(
    payload: ProjectCreate,
    current_user: CurrentUserDep,
    project_service: ProjectServiceDep,
) -> ApiResponse[ProjectRead]:
    project = await project_service.create_project(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
    )
    return ok(ProjectRead.model_validate(project))


@router.get(
    "",
    response_model=ApiResponse[Page[ProjectRead]],
    summary="List the caller's research workspaces",
)
async def list_projects(
    pagination: PaginationQuery,
    current_user: CurrentUserDep,
    project_service: ProjectServiceDep,
) -> ApiResponse[Page[ProjectRead]]:
    projects, total = await project_service.list_projects(
        owner_id=current_user.id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginated(
        [ProjectRead.model_validate(project) for project in projects],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{project_id}",
    response_model=ApiResponse[ProjectRead],
    summary="Get a research workspace",
)
async def get_project(project: ProjectInScopeDep) -> ApiResponse[ProjectRead]:
    return ok(ProjectRead.model_validate(project))


@router.delete(
    "/{project_id}",
    response_model=ApiResponse[None],
    summary="Delete a research workspace and all its content",
)
async def delete_project(
    project: ProjectInScopeDep,
    current_user: CurrentUserDep,
    project_service: ProjectServiceDep,
) -> ApiResponse[None]:
    await project_service.delete_project(project.id, owner_id=current_user.id)
    return ok(None)
