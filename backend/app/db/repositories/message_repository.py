"""Query object for the ``messages`` aggregate (design §6.6, §7.5)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message, MessageRole


class MessageRepository:
    """Persistence for :class:`Message`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        citations: list[dict[str, Any]] | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations or [],
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def list_for_conversation(
        self, conversation_id: UUID, *, limit: int = 20
    ) -> list[Message]:
        """Most recent turns, oldest-first, for follow-up resolution
        (design §4.5 "recent turns are injected for follow-up resolution")."""
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(reversed(result.scalars().all()))
