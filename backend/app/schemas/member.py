"""Wire contracts for project membership (Phase 10, FR-H6)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.project_member import ProjectRole
from app.services.membership_service import MemberView


class MemberInvite(BaseModel):
    """Payload for ``POST /projects/{id}/members``.

    The invitee must already have an account; there is no email delivery in this
    system, so the invitation takes effect immediately.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    role: ProjectRole = Field(
        default=ProjectRole.VIEWER,
        description="editor or viewer — ownership is never granted by invitation",
    )


class MemberRoleUpdate(BaseModel):
    """Payload for ``PATCH /projects/{id}/members/{member_id}``."""

    role: ProjectRole


class MemberRead(BaseModel):
    """One project member. ``id`` is null for the owner, who has no row."""

    model_config = ConfigDict(frozen=True)

    id: UUID | None
    user_id: UUID
    email: EmailStr
    name: str
    role: ProjectRole
    invited_at: datetime

    @classmethod
    def from_view(cls, view: MemberView) -> MemberRead:
        return cls(
            id=view.id,
            user_id=view.user_id,
            email=view.email,
            name=view.name,
            role=view.role,
            invited_at=view.invited_at,
        )
