"""``projects`` table — the tenancy boundary for all content (design §7.2, §7.5)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.document import Document
    from app.db.models.user import User


class Project(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A research workspace. Every document, conversation, and report reaches
    the tenancy boundary through this table's foreign key."""

    __tablename__ = "projects"
    __table_args__ = (
        # Serves the dashboard listing (design §7.4): a user's own projects,
        # most recent first.
        Index("ix_projects_owner_id_created_at", "owner_id", "created_at"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[User] = relationship(back_populates="projects")
    documents: Mapped[list[Document]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Document.uploaded_at.desc()",
    )
    conversations: Mapped[list[Conversation]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Conversation.created_at.desc()",
    )
