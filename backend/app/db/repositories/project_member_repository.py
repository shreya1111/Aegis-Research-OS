"""Query object for the ``project_members`` aggregate (Phase 10, FR-H6)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_member import ProjectMember


class ProjectMemberRepository:
    """Persistence for :class:`ProjectMember`, always scoped to a project."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        role: str,
        invited_by: UUID | None,
    ) -> ProjectMember:
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )
        self._session.add(member)
        await self._session.flush()
        return member

    async def get_for_user(self, project_id: UUID, *, user_id: UUID) -> ProjectMember | None:
        """Return the caller's membership row, if any.

        The project *owner* has no row here by default — ownership is intrinsic
        to ``projects.owner_id`` — so a ``None`` result means "not an invited
        member", not "no access". Role resolution combines both sources.
        """
        statement = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, member_id: UUID, *, project_id: UUID) -> ProjectMember | None:
        statement = select(ProjectMember).where(
            ProjectMember.id == member_id,
            ProjectMember.project_id == project_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_user_in_projects(
        self, *, user_id: UUID, project_ids: list[UUID]
    ) -> list[ProjectMember]:
        """Return one user's memberships across several projects in one query.

        Used by the dashboard listing to resolve the caller's role for a whole
        page of projects without a query per row.
        """
        if not project_ids:
            return []
        statement = select(ProjectMember).where(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id.in_(project_ids),
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_for_project(self, *, project_id: UUID) -> list[ProjectMember]:
        statement = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.invited_at)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def delete(self, member: ProjectMember) -> None:
        await self._session.delete(member)
        await self._session.flush()
