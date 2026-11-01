"""Project-scope dependencies (design §6.3, §9.3, §2.2).

Resolves ``{project_id}`` in a project-scoped route path and authorises it before
the handler body runs. Phase 10 widened access from ownership to membership:
a caller reaches a project through ownership *or* an invitation, and the
effective role decides which actions they may take.

Two properties are deliberate:

* A project outside the caller's access is indistinguishable from one that does
  not exist — both raise ``NotFoundError`` → 404 (design §9.3 rule 4).
* Role checks live here, in one place, and routers never inspect roles
  themselves. The frontend hides unavailable actions, but that is a UX
  affordance; this is the security boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.api.deps import CurrentUserDep, MembershipServiceDep, ProjectServiceDep
from app.core.errors import NotFoundError, PermissionDeniedError
from app.db.models.project import Project
from app.db.models.project_member import ProjectRole


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """The resolved project plus the caller's effective role within it."""

    project: Project
    role: ProjectRole


async def get_project_context(
    project_id: UUID,
    current_user: CurrentUserDep,
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ProjectContext:
    """Resolve ``{project_id}`` for the caller, or raise 404.

    Membership is resolved here rather than in each handler, so a role check
    never costs a second query and no route can accidentally skip it.
    """
    return await resolve_project_access(
        project_id,
        user_id=current_user.id,
        project_service=project_service,
        membership_service=membership_service,
    )


async def resolve_project_access(
    project_id: UUID,
    *,
    user_id: UUID,
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ProjectContext:
    """Resolve a caller's access to one project, or raise 404.

    Also used by the few routes that authorise *after* loading their resource
    (``/documents/{id}``, ``/reports/{id}``): they call this with the resource's
    own ``project_id``, so membership rules live in exactly one place.
    """
    project = await project_service.get_project_for_member(project_id, user_id=user_id)
    role = await membership_service.resolve_role(project, user_id=user_id)
    if role is None:
        # Unreachable through ``get_project_for_member``, but stated explicitly so
        # a later relaxation of that query cannot silently open a project route.
        raise NotFoundError("Project not found.")
    return ProjectContext(project=project, role=role)


ProjectContextDep = Annotated[ProjectContext, Depends(get_project_context)]


def _require(context: ProjectContext, minimum: ProjectRole) -> None:
    if not context.role.at_least(minimum):
        raise PermissionDeniedError(
            f"This action requires the {minimum.value} role on this project."
        )


async def get_project_in_scope(context: ProjectContextDep) -> Project:
    """The project, for any member — owner, editor, or viewer."""
    return context.project


async def get_editor_project(context: ProjectContextDep) -> Project:
    """The project, for callers holding at least the ``editor`` role."""
    _require(context, ProjectRole.EDITOR)
    return context.project


async def get_owner_project(context: ProjectContextDep) -> Project:
    """The project, for the owner only — membership management and deletion."""
    _require(context, ProjectRole.OWNER)
    return context.project


ProjectInScopeDep = Annotated[Project, Depends(get_project_in_scope)]
ProjectEditorDep = Annotated[Project, Depends(get_editor_project)]
ProjectOwnerDep = Annotated[Project, Depends(get_owner_project)]
