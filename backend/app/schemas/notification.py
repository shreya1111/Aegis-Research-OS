"""Wire contracts for in-app notifications (Phase 10, FR-H8)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.notification import Notification


class NotificationRead(BaseModel):
    """One notification for the signed-in user."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    project_id: UUID | None
    type: str
    title: str
    message: str
    link: str | None
    read: bool
    created_at: datetime

    @classmethod
    def from_model(cls, notification: Notification) -> NotificationRead:
        return cls(
            id=notification.id,
            project_id=notification.project_id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            link=notification.link,
            read=notification.read,
            created_at=notification.created_at,
        )


class NotificationInbox(BaseModel):
    """The inbox plus the unread badge count, in one response."""

    model_config = ConfigDict(frozen=True)

    items: list[NotificationRead]
    unread: int
