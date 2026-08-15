"""Async SQLAlchemy engine and per-request session management (design §6.6)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, created once.

    ``pool_pre_ping`` guards against stale connections after the database
    restarts; harmless overhead for the connection volume this system expects.
    """
    settings = get_settings()
    return create_async_engine(str(settings.postgres_url), pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory bound to :func:`get_engine`."""
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one session per request.

    Commits on success, rolls back on any exception, and always closes — a
    handler never manages transaction boundaries directly.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def new_db_session() -> AsyncIterator[AsyncSession]:
    """Open an independent session for code that runs outside a request.

    Background tasks (design §6.7) run after the request's own session has
    already closed, so they need their own transaction boundary rather than
    reusing a request-scoped session.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def reset_engine_cache(settings: Settings | None = None) -> None:
    """Dispose cached engine/session-factory state.

    Used by tests that construct a differently configured engine; not called
    in normal application operation.
    """
    del settings
    get_engine.cache_clear()
    get_session_factory.cache_clear()
