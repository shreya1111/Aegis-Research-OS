"""Persistence: SQLAlchemy models, repositories, session management, migrations.

Repositories are the only place raw SQL — including pgvector similarity and
full-text search — is written, which keeps the tenancy boundary auditable in one
location.
"""
