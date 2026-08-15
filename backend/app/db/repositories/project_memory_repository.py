"""Query object for the ``project_memory`` aggregate (design §6.6, §4.5)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_memory import ProjectMemory


class ProjectMemoryRepository:
    """Persistence for :class:`ProjectMemory`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, project_id: UUID, fact: str, citations: list[dict[str, Any]]
    ) -> ProjectMemory:
        record = ProjectMemory(project_id=project_id, fact=fact, citations=citations)
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_for_project(self, project_id: UUID, *, limit: int = 50) -> list[ProjectMemory]:
        """Most recent facts first (design §4.5: a digest, never a raw dump —
        the caller truncates/filters further before injecting into context)."""
        statement = (
            select(ProjectMemory)
            .where(ProjectMemory.project_id == project_id)
            .order_by(ProjectMemory.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
