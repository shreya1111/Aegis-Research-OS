"""Query object for the ``notifications`` aggregate (Phase 10, FR-H8)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification


class NotificationRepository:
    """Persistence for per-user in-app notifications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        project_id: UUID | None = None,
        link: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            project_id=project_id,
            type=type,
            title=title,
            message=message,
            link=link,
        )
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def list_for_user(self, *, user_id: UUID, limit: int = 20) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def count_unread(self, *, user_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read.is_(False))
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def mark_read(self, notification_id: UUID, *, user_id: UUID) -> bool:
        """Mark one notification read, scoped to its owner.

        Returns ``False`` when no such notification belongs to ``user_id`` — the
        caller maps that to 404, so one user's notification ids are not
        probeable by another (design §9.3 rule 4).
        """
        statement = (
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(read=True)
        )
        result = await self._session.execute(statement)
        await self._session.flush()
        return bool(result.rowcount)
