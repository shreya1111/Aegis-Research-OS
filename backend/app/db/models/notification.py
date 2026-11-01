"""``notifications`` table — in-app completion notices (Phase 10, FR-H8).

A long-running generation (a report artifact) is dispatched as a background
task, so the user needs a way to learn it finished without watching the page.
Rows here are per-user, optionally linked to the project and artifact they
refer to.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class NotificationType:
    """Canonical notification kinds (constants — see ``ActivityAction``)."""

    REPORT_COMPLETED = "report.completed"
    MEMBER_ADDED = "member.added"


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One in-app notification for one user."""

    __tablename__ = "notifications"
    __table_args__ = (
        # Unread badge: a user's newest unread notifications.
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
        Index("ix_notifications_read", "read"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    #: In-app path to the related entity, e.g. ``/projects/<id>/reports``.
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
