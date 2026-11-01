"""``/projects`` router: CRUD for research workspaces (design §6.5, FR-B)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, MembershipServiceDep, ProjectServiceDep
from app.api.v1.deps import ProjectContextDep, ProjectOwnerDep
from app.core.envelope import ok, paginated
from app.db.models.project_member import ProjectRole
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
    # The creator is always the owner, so the role is known without a lookup.
    return ok(ProjectRead.from_model(project, ProjectRole.OWNER))


@router.get(
    "",
    response_model=ApiResponse[Page[ProjectRead]],
    summary="List the research workspaces the caller may access",
)
async def list_projects(
    pagination: PaginationQuery,
    current_user: CurrentUserDep,
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[Page[ProjectRead]]:
    projects, total = await project_service.list_projects(
        owner_id=current_user.id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    # One query resolves roles for the whole page, so the dashboard can render
    # shared projects differently from owned ones without an N+1 lookup.
    roles = await membership_service.roles_for(projects, user_id=current_user.id)
    items = [
        ProjectRead.from_model(project, roles.get(project.id)) for project in projects
    ]
    return paginated(
        items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/{project_id}",
    response_model=ApiResponse[ProjectRead],
    summary="Get a research workspace",
)
async def get_project(context: ProjectContextDep) -> ApiResponse[ProjectRead]:
    return ok(ProjectRead.from_model(context.project, context.role))


@router.delete(
    "/{project_id}",
    response_model=ApiResponse[None],
    summary="Delete a research workspace and all its content",
)
async def delete_project(
    project: ProjectOwnerDep,
    project_service: ProjectServiceDep,
) -> ApiResponse[None]:
    """Delete a project. Owner-only: sharing a project does not grant the right
    to destroy it, and the cascade takes every collaborator's content with it."""
    await project_service.delete_project(project.id, owner_id=project.owner_id)
    return ok(None)
