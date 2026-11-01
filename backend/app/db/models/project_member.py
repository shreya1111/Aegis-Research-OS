"""``project_members`` table — per-project collaboration roles (Phase 10, FR-H6).

Ownership stays intrinsic to ``projects.owner_id``; this table records the
*additional* members a project has been shared with, and their role. Resolving a
caller's effective role therefore consults both sources, which keeps existing
owner-only projects correct without a data backfill (see
:class:`~app.services.membership_service.MembershipService`).

Role enforcement is server-side on every project-scoped route (design §2.2):
the frontend hides unavailable actions, but hiding is a UX affordance, never the
security boundary.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class ProjectRole(StrEnum):
    """Roles a caller can hold within one project (design §2.2).

    Ordered by capability: an owner may do everything an editor may, and an
    editor everything a viewer may. :attr:`rank` encodes that ordering so
    "at least this role" checks are a single comparison rather than a set
    membership test that has to be kept in sync by hand.
    """

    VIEWER = "viewer"
    EDITOR = "editor"
    OWNER = "owner"

    @property
    def rank(self) -> int:
        return _ROLE_RANK[self]

    def at_least(self, required: ProjectRole) -> bool:
        return self.rank >= required.rank


_ROLE_RANK: dict[ProjectRole, int] = {
    ProjectRole.VIEWER: 1,
    ProjectRole.EDITOR: 2,
    ProjectRole.OWNER: 3,
}


class ProjectMember(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One user's membership of one project, with a role."""

    __tablename__ = "project_members"
    __table_args__ = (
        # A user holds at most one role per project.
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        Index("ix_project_members_project_id", "project_id"),
        Index("ix_project_members_user_id", "user_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Stored as text for a readable audit trail; validated against
    #: :class:`ProjectRole` in the service layer.
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    #: ``NULL`` for a membership not created through an invite (e.g. a
    #: backfilled owner row), and set to the inviter otherwise.
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    #: Eager-loaded: the members list renders every member's email and name, and
    #: a lazy load would raise under the async session rather than fetching.
    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined")

    @property
    def role_value(self) -> ProjectRole:
        """The membership's role as an enum value."""
        return ProjectRole(self.role)
