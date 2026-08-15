"""Document intelligence: documents and document_chunks tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-30

Phase 3 (design §7.2, §7.4, §8, FR-C). ``document_chunks.embedding`` uses the
pgvector extension enabled by migration 0001.

Implementation note on the vector index: design §7.4 describes a "composite ANN
index (project_id, embedding)". pgvector's HNSW/IVFFlat indexes are built over
the vector column only — there is no multi-column (scalar + vector) ANN index
type to create. The smallest reasonable implementation of that intent is an
HNSW index on `embedding` alone, combined with the existing btree index on
`project_id` (already present for FTS/tenancy scoping); Postgres can use the
btree to restrict the candidate set and the HNSW index for similarity ranking.
This is noted here rather than silently deviating from the stated design.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Must match `Settings.embedding_dimensions` (all-MiniLM-L6-v2 = 384). The
#: column type is a migration-time decision, not a per-request one (design §4.3).
EMBEDDING_DIMENSIONS = 384


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_documents_project_id_uploaded_at", "documents", ["project_id", "uploaded_at"]
    )
    op.create_index("ix_documents_project_id_status", "documents", ["project_id", "status"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=True),
        sa.Column("source_ref", postgresql.JSONB(), nullable=False),
        sa.Column(
            "content_tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_document_chunks_document_id_chunk_index",
        "document_chunks",
        ["document_id", "chunk_index"],
    )
    op.create_index("ix_document_chunks_project_id", "document_chunks", ["project_id"])
    op.create_index(
        "ix_document_chunks_content_tsv",
        "document_chunks",
        ["content_tsv"],
        postgresql_using="gin",
    )
    # HNSW ANN index for semantic search (design §4.4, §7.4). Built here even
    # though the table starts empty: HNSW (unlike IVFFlat) builds and refines
    # incrementally rather than needing representative training data, so an
    # empty-table build is not the poor-structure concern design §7.4 flags
    # for IVFFlat-style indexes.
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.drop_index("ix_document_chunks_content_tsv", table_name="document_chunks")
    op.drop_index("ix_document_chunks_project_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id_chunk_index", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_project_id_status", table_name="documents")
    op.drop_index("ix_documents_project_id_uploaded_at", table_name="documents")
    op.drop_table("documents")
