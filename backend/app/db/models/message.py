"""``messages`` table (design §7.2).

Chat history with citations preserved. ``citations`` is the record that makes
citation validity auditable after the fact (design §8.8 step 7).
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent_trace import AgentTrace
    from app.db.models.conversation import Conversation


class MessageRole(StrEnum):
    """Design §7.2: ``role`` is ``user`` | ``assistant``."""

    USER = "user"
    ASSISTANT = "assistant"


class Message(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One turn in a conversation (design §7.2)."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_id_created_at", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MessageRole] = mapped_column(String(20), nullable=False)
    #: Markdown for assistant messages (design §7.2).
    content: Mapped[str] = mapped_column(Text, nullable=False)
    #: Ordered list of `{marker, chunk_id?, document_id?, external_source?,
    #: page}` (design §7.2) — empty for user messages.
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    traces: Mapped[list[AgentTrace]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AgentTrace.created_at",
    )
