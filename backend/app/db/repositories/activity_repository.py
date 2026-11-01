"""Query object for the ``activity_log`` aggregate (Phase 10, FR-H7)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.activity import ActivityLog


class ActivityRepository:
    """Append-only audit trail, read one project at a time."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: UUID,
        user_id: UUID | None,
        action: str,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        context: dict[str, Any] | None = None,
    ) -> ActivityLog:
        entry = ActivityLog(
            project_id=project_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            context=context,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_for_project(
        self, *, project_id: UUID, offset: int, limit: int
    ) -> tuple[list[ActivityLog], int]:
        """Return one page of a project's audit entries, newest first, plus the total."""
        items_statement = (
            select(ActivityLog)
            .where(ActivityLog.project_id == project_id)
            .order_by(ActivityLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = (
            select(func.count())
            .select_from(ActivityLog)
            .where(ActivityLog.project_id == project_id)
        )

        items_result = await self._session.execute(items_statement)
        total_result = await self._session.execute(count_statement)

        return list(items_result.scalars().all()), int(total_result.scalar_one())
