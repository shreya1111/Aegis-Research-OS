"""Query object for the ``projects`` aggregate (design §6.6, §7.5).

Every method that touches project content requires the owner's id, making a
cross-tenant query unwritable through this API (design §9.3 rule 3).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import Project


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
