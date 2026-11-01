"""Project membership and role resolution (Phase 10, FR-H6, design §2.2).

Ownership remains intrinsic to ``projects.owner_id``; this service treats the
owner as an implicit, non-removable member and layers invited members on top.
That keeps owner-only projects correct with no data backfill, and gives callers
one place to ask "what may this user do here?".

Every method here is pure business logic: routers authorise by calling
:meth:`MembershipService.require`, and never inspect roles themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.db.models.project import Project
from app.db.models.project_member import ProjectMember, ProjectRole
from app.db.repositories.project_member_repository import ProjectMemberRepository
from app.db.repositories.user_repository import UserRepository


@dataclass(frozen=True, slots=True)
class MemberView:
    """One member of a project, owner included.

    ``id`` is the membership row's id, and is ``None`` for the owner, who has no
    row — the UI uses it as a key and disables mutating controls when it is
    absent or when the role is ``owner``.
    """

    id: UUID | None
    user_id: UUID
    email: str
    name: str
    role: ProjectRole
    invited_at: datetime


class MembershipService:
    """Roles, invitations, and membership listing for one project at a time."""

    def __init__(
        self,
        *,
        member_repository: ProjectMemberRepository,
        user_repository: UserRepository,
    ) -> None:
        self._members = member_repository
        self._users = user_repository

    async def resolve_role(self, project: Project, *, user_id: UUID) -> ProjectRole | None:
        """Return ``user_id``'s effective role on ``project``, or ``None``.

        ``None`` means "no access" — callers turn that into 404, never 403, so
        the existence of another user's project is not disclosed (design §9.3).
        """
        if project.owner_id == user_id:
            return ProjectRole.OWNER
        membership = await self._members.get_for_user(project.id, user_id=user_id)
        if membership is None:
            return None
        return membership.role_value

    async def roles_for(
        self, projects: list[Project], *, user_id: UUID
    ) -> dict[UUID, ProjectRole]:
        """Resolve the caller's role for several projects at once.

        One query covers the invited memberships; ownership is read straight off
        the projects. Projects the caller reaches through neither path are
        simply absent from the result, so the caller renders them without a role
        rather than inventing one.
        """
        roles: dict[UUID, ProjectRole] = {
            project.id: ProjectRole.OWNER
            for project in projects
            if project.owner_id == user_id
        }
        invited_ids = [project.id for project in projects if project.id not in roles]
        if invited_ids:
            memberships = await self._members.list_for_user_in_projects(
                user_id=user_id, project_ids=invited_ids
            )
            for membership in memberships:
                roles[membership.project_id] = membership.role_value
        return roles

    async def require(
        self, project: Project, *, user_id: UUID, minimum: ProjectRole
    ) -> ProjectRole:
        """Return the caller's role, or raise if it is below ``minimum``.

        Raises
        ------
        PermissionDeniedError
            If the caller holds a role weaker than ``minimum`` (403). Reachable
            only for a caller the scope dependency already admitted; a caller
            with no access at all is rejected earlier as 404.
        """
        role = await self.resolve_role(project, user_id=user_id)
        if role is None or not role.at_least(minimum):
            raise PermissionDeniedError(
                f"This action requires the {minimum.value} role on this project."
            )
        return role

    async def list_members(self, project: Project) -> list[MemberView]:
        """Return the owner first, then invited members in invitation order."""
        owner = await self._users.get_by_id(project.owner_id)
        memberships = await self._members.list_for_project(project_id=project.id)

        views: list[MemberView] = []
        if owner is not None:
            views.append(
                MemberView(
                    id=None,
                    user_id=owner.id,
                    email=owner.email,
                    name=owner.name,
                    role=ProjectRole.OWNER,
                    invited_at=project.created_at,
                )
            )
        for membership in memberships:
            # ``ProjectMember.user`` is join-loaded by the model, so this is one
            # query for the whole list rather than a lazy load per row.
            user = membership.user
            views.append(
                MemberView(
                    id=membership.id,
                    user_id=user.id,
                    email=user.email,
                    name=user.name,
                    role=membership.role_value,
                    invited_at=membership.invited_at,
                )
            )
        return views

    async def invite(
        self,
        project: Project,
        *,
        inviter_id: UUID,
        email: str,
        role: ProjectRole,
    ) -> ProjectMember:
        """Add an existing account to ``project`` with ``role``.

        Invitations are applied immediately rather than stored pending: the
        account must already exist, and the added user sees the project on their
        next dashboard load (Phase 10 acceptance criterion).

        Raises
        ------
        NotFoundError
            If no account exists for ``email``.
        ConflictError
            If the user already has access to the project.
        """
        if role is ProjectRole.OWNER:
            # Ownership is transferred, never granted by invitation — an
            # invitation must not create a second owner.
            raise ConflictError("A project has exactly one owner; invite an editor or viewer.")

        user = await self._users.get_by_email(email)
        if user is None:
            raise NotFoundError("No account exists with that email address.")

        if user.id == project.owner_id:
            raise ConflictError("That user already owns this project.")

        existing = await self._members.get_for_user(project.id, user_id=user.id)
        if existing is not None:
            raise ConflictError("That user is already a member of this project.")

        return await self._members.create(
            project_id=project.id,
            user_id=user.id,
            role=role.value,
            invited_by=inviter_id,
        )

    async def change_role(
        self, project: Project, *, member_id: UUID, role: ProjectRole
    ) -> ProjectMember:
        """Change an invited member's role.

        The owner has no membership row, so an owner target is naturally a 404 —
        ownership is never editable through this path.
        """
        if role is ProjectRole.OWNER:
            raise ConflictError("Ownership cannot be granted through a role change.")

        member = await self._members.get_by_id(member_id, project_id=project.id)
        if member is None:
            raise NotFoundError("Member not found.")

        member.role = role.value
        return member

    async def remove_member(self, project: Project, *, member_id: UUID) -> None:
        """Remove an invited member. The owner cannot be removed."""
        member = await self._members.get_by_id(member_id, project_id=project.id)
        if member is None:
            raise NotFoundError("Member not found.")
        await self._members.delete(member)
