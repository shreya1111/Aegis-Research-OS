"""``/projects/{id}/members`` — collaboration roles and invitations (Phase 10, FR-H6).

Reading the roster is open to every member of the project; changing it is
owner-only. Mutations return the refreshed roster rather than a single row,
because the members panel renders the whole list and a roster page is already
paid for by the request.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import (
    ActivityServiceDep,
    CurrentUserDep,
    MembershipServiceDep,
    NotificationServiceDep,
)
from app.api.v1.deps import ProjectInScopeDep, ProjectOwnerDep
from app.core.envelope import ok
from app.db.models.activity import ActivityAction
from app.db.models.notification import NotificationType
from app.db.models.project import Project
from app.schemas.common import ApiResponse
from app.schemas.member import MemberInvite, MemberRead, MemberRoleUpdate

router = APIRouter(tags=["members"])


async def _roster(project: Project, membership_service: MembershipServiceDep) -> list[MemberRead]:
    members = await membership_service.list_members(project)
    return [MemberRead.from_view(member) for member in members]


@router.get(
    "/projects/{project_id}/members",
    response_model=ApiResponse[list[MemberRead]],
    summary="List the project's members and their roles",
)
async def list_members(
    project: ProjectInScopeDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[list[MemberRead]]:
    return ok(await _roster(project, membership_service))


@router.post(
    "/projects/{project_id}/members",
    response_model=ApiResponse[list[MemberRead]],
    status_code=status.HTTP_201_CREATED,
    summary="Add an existing account to the project",
)
async def invite_member(
    project: ProjectOwnerDep,
    payload: MemberInvite,
    current_user: CurrentUserDep,
    membership_service: MembershipServiceDep,
    activity_service: ActivityServiceDep,
    notification_service: NotificationServiceDep,
) -> ApiResponse[list[MemberRead]]:
    """Add a user to the project with an editor or viewer role.

    The invitation takes effect immediately: there is no email delivery, so the
    invitee finds the project on their next dashboard load.
    """
    member = await membership_service.invite(
        project,
        inviter_id=current_user.id,
        email=str(payload.email),
        role=payload.role,
    )

    await activity_service.record(
        project_id=project.id,
        user_id=current_user.id,
        action=ActivityAction.MEMBER_INVITED,
        entity_type="member",
        entity_id=member.id,
        context={"email": str(payload.email), "role": payload.role.value},
    )
    await notification_service.notify(
        user_id=member.user_id,
        project_id=project.id,
        type=NotificationType.MEMBER_ADDED,
        title="Added to a project",
        message=f"You were added to “{project.title}” as {payload.role.value}.",
        link=f"/projects/{project.id}",
    )

    return ok(await _roster(project, membership_service))


@router.patch(
    "/projects/{project_id}/members/{member_id}",
    response_model=ApiResponse[list[MemberRead]],
    summary="Change a member's role",
)
async def update_member_role(
    project: ProjectOwnerDep,
    member_id: UUID,
    payload: MemberRoleUpdate,
    current_user: CurrentUserDep,
    membership_service: MembershipServiceDep,
    activity_service: ActivityServiceDep,
) -> ApiResponse[list[MemberRead]]:
    member = await membership_service.change_role(
        project, member_id=member_id, role=payload.role
    )
    await activity_service.record(
        project_id=project.id,
        user_id=current_user.id,
        action=ActivityAction.MEMBER_ROLE_CHANGED,
        entity_type="member",
        entity_id=member.id,
        context={"role": payload.role.value},
    )
    return ok(await _roster(project, membership_service))


@router.delete(
    "/projects/{project_id}/members/{member_id}",
    response_model=ApiResponse[list[MemberRead]],
    summary="Remove a member from the project",
)
async def remove_member(
    project: ProjectOwnerDep,
    member_id: UUID,
    current_user: CurrentUserDep,
    membership_service: MembershipServiceDep,
    activity_service: ActivityServiceDep,
) -> ApiResponse[list[MemberRead]]:
    """Remove an invited member. The owner cannot be removed — there is no row."""
    await membership_service.remove_member(project, member_id=member_id)
    await activity_service.record(
        project_id=project.id,
        user_id=current_user.id,
        action=ActivityAction.MEMBER_REMOVED,
        entity_type="member",
        entity_id=member_id,
    )
    return ok(await _roster(project, membership_service))
