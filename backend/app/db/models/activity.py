"""``activity_log`` table — per-project audit trail (Phase 10, FR-H7).

One row per user-visible action: a document uploaded or deleted, a question
asked, an artifact generated, a member added or removed. The log is append-only
and project-scoped, so reading it is gated by the same tenancy predicate as
everything else (design §7.5).

Only summaries are stored — never document text or question content beyond the
action label — matching the ``agent_traces`` privacy decision (design §6.9).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class ActivityAction:
    """Canonical action names written to the audit log.

    Constants rather than an enum column: the log is a historical record, so a
    new action type must never invalidate rows written by an older build.
    """

    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_DELETED = "document.deleted"
    QUERY_EXECUTED = "query.executed"
    REPORT_GENERATED = "report.generated"
    REPORT_FAILED = "report.failed"
    MEMBER_INVITED = "member.invited"
    MEMBER_ROLE_CHANGED = "member.role_changed"
    MEMBER_REMOVED = "member.removed"


class ActivityLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One audit entry for one project."""

    __tablename__ = "activity_log"
    __table_args__ = (
        # Activity tab: a project's entries, newest first (Phase 10).
        Index("ix_activity_log_project_id_created_at", "project_id", "created_at"),
        Index("ix_activity_log_user_id", "user_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Nullable so an entry survives the deletion of the user who made it —
    #: the audit trail must outlive the account (``ON DELETE SET NULL``).
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    #: ``document`` | ``report`` | ``query`` | ``member`` | ``project``.
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    #: Small structured context for display (e.g. ``{"filename": "paper.pdf"}``).
    #: Mapped to the ``metadata`` column the migration created; the attribute is
    #: named ``context`` because ``metadata`` is reserved on declarative classes.
    context: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    #: Eager-loaded so the Activity tab renders actor names without a lazy load
    #: under the async session (which would raise rather than fetch).
    actor: Mapped[User | None] = relationship(lazy="joined")
