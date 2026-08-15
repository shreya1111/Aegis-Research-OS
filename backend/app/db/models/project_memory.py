"""``project_memory`` table (design §4.5, §7.2, Phase 5).

Project-scoped long-term memory: durable, source-backed facts distilled by the
Memory agent. Speculative or unverified statements are never promoted here
(design §4.5 "Memory agent contract").
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ProjectMemory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One durable, cited fact accumulated for a project (design §4.5)."""

    __tablename__ = "project_memory"
    __table_args__ = (Index("ix_project_memory_project_id_created_at", "project_id", "created_at"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    #: Same citation shape as `messages.citations` — a fact recalled from
    #: memory stays traceable to a document (design §4.5).
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
