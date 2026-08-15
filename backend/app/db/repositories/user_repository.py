"""Query object for the ``users`` aggregate (design §6.6)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class UserRepository:
    """Persistence for :class:`User`. No business logic — see ``AuthService``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email.lower())
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, *, email: str, hashed_password: str, name: str) -> User:
        user = User(email=email.lower(), hashed_password=hashed_password, name=name)
        self._session.add(user)
        await self._session.flush()
        return user
