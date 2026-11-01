"""Query object for the ``projects`` aggregate (design §6.6, §7.5).

Every method that touches project content requires the owner's id, making a
cross-tenant query unwritable through this API (design §9.3 rule 3).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import Project
from app.db.models.project_member import ProjectMember


class ProjectRepository:
    """Persistence for :class:`Project`, scoped to an owner on every read."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, owner_id: UUID, title: str, description: str | None) -> Project:
        project = Project(owner_id=owner_id, title=title, description=description)
        self._session.add(project)
        await self._session.flush()
        return project

    async def get_by_id_for_owner(self, project_id: UUID, *, owner_id: UUID) -> Project | None:
        """Fetch a project only if ``owner_id`` owns it.

        Returning ``None`` for a project that exists but belongs to someone
        else is deliberate: the caller maps a miss to 404, never 403, so
        resource existence is not disclosed (design §9.3 rule 4).
        """
        statement = select(Project).where(
            Project.id == project_id,
            Project.owner_id == owner_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id_for_member(self, project_id: UUID, *, user_id: UUID) -> Project | None:
        """Fetch a project the caller may access, as owner or as a member.

        Phase 10 widens the scope predicate from ownership to membership
        (design §2.2): the owner is resolved from ``projects.owner_id`` and
        invited members from ``project_members``. A project the caller can
        reach through neither path is still returned as ``None``, so the caller
        maps it to 404 and never discloses existence (design §9.3 rule 4).
        """
        statement = select(Project).where(
            Project.id == project_id,
            or_(
                Project.owner_id == user_id,
                Project.id.in_(
                    select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
                ),
            ),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_member(
        self, *, user_id: UUID, offset: int, limit: int
    ) -> tuple[list[Project], int]:
        """Return one page of the projects a caller may access, newest first.

        The dashboard lists accessible workspaces — owned *and* shared — since
        an invited user must be able to find the project they were added to
        (Phase 10 acceptance criterion, FR-B2).
        """
        scope = or_(
            Project.owner_id == user_id,
            Project.id.in_(
                select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
            ),
        )
        items_statement = (
            select(Project)
            .where(scope)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = select(func.count()).select_from(Project).where(scope)

        items_result = await self._session.execute(items_statement)
        total_result = await self._session.execute(count_statement)

        return list(items_result.scalars().all()), int(total_result.scalar_one())

    async def list_for_owner(
        self, *, owner_id: UUID, offset: int, limit: int
    ) -> tuple[list[Project], int]:
        """Return one page of an owner's projects, most recent first, plus the total."""
        items_statement = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = (
            select(func.count()).select_from(Project).where(Project.owner_id == owner_id)
        )

        items_result = await self._session.execute(items_statement)
        total_result = await self._session.execute(count_statement)

        return list(items_result.scalars().all()), int(total_result.scalar_one())

    async def delete(self, project: Project) -> None:
        """Delete a project. Cascades to its content at the database level."""
        await self._session.delete(project)
        await self._session.flush()
