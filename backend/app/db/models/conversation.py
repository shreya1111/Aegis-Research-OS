"""``conversations`` table (design §7.2).

Chat history container, project-scoped. A conversation groups the messages of
one ongoing exchange; its ``title`` is derived from the first message.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.message import Message


class Conversation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A chat thread within a project (design §7.2)."""

    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_project_id_created_at", "project_id", "created_at"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Derived from the first message; nullable until that message exists.
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )
