"""Audit-trail recording (Phase 10, FR-H7).

Routers call :meth:`ActivityService.record` after an action succeeds, so the log
reflects what actually happened rather than what was attempted. The service is
deliberately thin: the value is in *always* recording the same way, not in the
recording itself.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.models.activity import ActivityLog
from app.db.repositories.activity_repository import ActivityRepository


class ActivityService:
    """Append user-visible actions to a project's audit log."""

    def __init__(self, *, activity_repository: ActivityRepository) -> None:
        self._activity = activity_repository

    async def record(
        self,
        *,
        project_id: UUID,
        user_id: UUID | None,
        action: str,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        await self._activity.create(
            project_id=project_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            context=context,
        )

    async def list_for_project(
        self, *, project_id: UUID, page: int, page_size: int
    ) -> tuple[list[ActivityLog], int]:
        """One page of a project's audit log, newest first, plus the total."""
        return await self._activity.list_for_project(
            project_id=project_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
