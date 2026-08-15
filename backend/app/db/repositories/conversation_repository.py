"""Query object for the ``conversations`` aggregate (design §6.6, §7.5)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation


class ConversationRepository:
    """Persistence for :class:`Conversation`, always project-scoped."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, project_id: UUID, title: str | None = None) -> Conversation:
        conversation = Conversation(project_id=project_id, title=title)
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get_by_id_for_project(
        self, conversation_id: UUID, *, project_id: UUID
    ) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id, Conversation.project_id == project_id
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_or_create_default(self, *, project_id: UUID) -> Conversation:
        """Return the project's most recent conversation, or create one.

        Phase 4's single-shot query endpoint does not expose conversation
        management yet — every query in a project lands in one running
        conversation so recent turns remain available for follow-up
        resolution (design §4.5 "Conversation-scoped" memory horizon).
        """
        statement = (
            select(Conversation)
            .where(Conversation.project_id == project_id)
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
        return await self.create(project_id=project_id)

    async def set_title_if_unset(self, conversation: Conversation, title: str) -> None:
        if conversation.title is None:
            conversation.title = title[:300]
            await self._session.flush()
