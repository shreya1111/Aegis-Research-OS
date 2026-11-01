"""Wire contract for the project audit log (Phase 10, FR-H7)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.activity import ActivityLog


class ActivityRead(BaseModel):
    """One audit entry, as shown in the Activity tab."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str | None
    entity_id: UUID | None
    context: dict[str, Any] | None
    created_at: datetime
    #: Display name of the actor, or ``None`` if the account was deleted — the
    #: log outlives the user (``ON DELETE SET NULL`` on ``user_id``).
    actor_name: str | None = None

    @classmethod
    def from_model(cls, entry: ActivityLog) -> ActivityRead:
        return cls(
            id=entry.id,
            user_id=entry.user_id,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            context=entry.context,
            created_at=entry.created_at,
            actor_name=entry.actor.name if entry.actor is not None else None,
        )
