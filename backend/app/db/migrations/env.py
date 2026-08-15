"""Alembic environment.

Reads the database URL from the application's typed settings rather than from
``alembic.ini``, so there is exactly one place a connection string is configured
(design §9.8). Runs migrations with a synchronous driver even though the
application uses ``asyncpg`` at runtime — Alembic's autogenerate and offline
modes are simplest against a sync engine, and DDL is not on the hot path.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_database_url() -> str:
    """Return the configured Postgres URL with a sync driver for Alembic."""
    return str(get_settings().postgres_url).replace(
        "postgresql+asyncpg://", "postgresql+psycopg2://"
    )


def run_migrations_offline() -> None:
    """Emit SQL without a live database connection (``alembic upgrade --sql``)."""
    context.configure(
        url=_sync_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _sync_database_url()

    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
