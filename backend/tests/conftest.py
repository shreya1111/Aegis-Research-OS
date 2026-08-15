"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings
from app.db.models import Base
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    """Deterministic test configuration, independent of the developer's ``.env``.

    Points at the dedicated ``aegis_test`` database and a fakeredis-backed cache
    (overridden per-app in :func:`app`), so integration tests never touch
    development data.
    """
    return Settings(
        environment="development",
        log_level="WARNING",
        cors_origins=["http://localhost:3000"],
        postgres_url="postgresql+asyncpg://aegis:local-dev-only-password@localhost:15432/aegis_test",
        jwt_secret="integration-test-secret-of-sufficient-length-32b",
        rate_limit_login_per_minute=1000,
        rate_limit_register_per_minute=1000,
    )


@pytest.fixture
async def db_engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    """A dedicated engine against the test database, schema created and dropped
    per test so integration tests never see another test's data.

    Enables the ``vector`` extension before creating tables — mirroring
    migration 0001's responsibility, since this fixture builds the schema
    from ORM metadata rather than by running Alembic (design §7: pgvector must
    exist before any ``vector`` column can be created).
    """
    engine = create_async_engine(str(settings.postgres_url), pool_pre_ping=True)
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
def app(
    settings: Settings,
    db_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[FastAPI]:
    """A freshly composed application instance per test, with Postgres and
    Redis overridden to point at test-scoped, disposable instances.

    Request-time consumers reach the database through the ``get_db_session``
    dependency, overridden here. Background tasks (design §6.7) instead open
    their own session via ``app.db.session.new_db_session`` → ``get_session_
    factory`` — so that factory is monkeypatched to the test engine too,
    ensuring ingestion in tests writes to ``aegis_test`` rather than the real
    development database.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.core.cache import RateLimiter, TokenDenylist, get_rate_limiter, get_token_denylist
    from app.db.session import get_db_session

    fake_redis = FakeRedis(decode_responses=True)
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # Background-task session source (design §6.7). ``new_db_session`` looks up
    # ``get_session_factory`` in its own module namespace at call time, so this
    # patch redirects background ingestion onto the test engine.
    monkeypatch.setattr("app.db.session.get_session_factory", lambda: session_factory)

    fastapi_app = create_app(settings)
    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    fastapi_app.dependency_overrides[get_token_denylist] = lambda: TokenDenylist(fake_redis)
    fastapi_app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(fake_redis)

    yield fastapi_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """In-process HTTP client — no network, no running server required."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
