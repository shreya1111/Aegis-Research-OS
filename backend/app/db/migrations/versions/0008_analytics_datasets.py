"""Analytics datasets table for Phase 8.

Revision ID: 0008
Revises: f3f6c804751d  
Create Date: 2026-10-04

Phase 8 introduces analytics/data science capabilities: CSV upload, profiling,
AI-assisted analysis, and chart generation.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | Sequence[str] | None = "f3f6c804751d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_datasets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),  # pending, profiled, failed
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("profile_data", postgresql.JSONB(), nullable=True),  # column types, stats, etc.
        sa.Column("file_path", sa.String(length=1000), nullable=False),  # storage path
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_analytics_datasets_project_id_created_at",
        "analytics_datasets",
        ["project_id", "created_at"],
    )
    
    op.create_table(
        "analytics_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("analysis_code", sa.Text(), nullable=True),  # Generated Python code
        sa.Column("result_data", postgresql.JSONB(), nullable=True),  # Analysis results
        sa.Column("chart_data", postgresql.JSONB(), nullable=True),  # Chart configuration
        sa.Column("explanation", sa.Text(), nullable=True),  # Plain-language explanation
        sa.Column("status", sa.String(length=20), nullable=False),  # pending, completed, failed
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["analytics_datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_analytics_analyses_dataset_id_created_at",
        "analytics_analyses",
        ["dataset_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_analyses_dataset_id_created_at", table_name="analytics_analyses")
    op.drop_table("analytics_analyses")
    op.drop_index("ix_analytics_datasets_project_id_created_at", table_name="analytics_datasets")
    op.drop_table("analytics_datasets")
