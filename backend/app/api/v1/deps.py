"""Project-scope dependency (design §6.3, §9.3).

Resolves ``{id}`` in a project-scoped route path and authorises it before the
handler body runs. A project outside the caller's ownership is indistinguishable
from one that does not exist: both raise ``NotFoundError`` → 404.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.api.deps import CurrentUserDep, ProjectServiceDep
from app.db.models.project import Project


async def get_project_in_scope(
    project_id: UUID,
    current_user: CurrentUserDep,
    project_service: ProjectServiceDep,
) -> Project:
    return await project_service.get_project(project_id, owner_id=current_user.id)


ProjectInScopeDep = Annotated[Project, Depends(get_project_in_scope)]
