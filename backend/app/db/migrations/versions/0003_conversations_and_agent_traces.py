"""Hybrid RAG and multi-agent system: conversations, messages, agent_traces,
project_memory tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31

Phase 4 (design §7.2, §6.1) introduces `conversations`/`messages` to persist
Q&A with citations. Phase 5 (design §4.5, §4.6) introduces `agent_traces` (the
observability spine) and `project_memory` (durable, cited facts the Memory
agent accumulates). All four ship together since `agent_traces.message_id`
references `messages`, and Phase 4's single-shot RAG path already writes
traces for its own (much shorter) pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_conversations_project_id_created_at", "conversations", ["project_id", "created_at"]
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_messages_conversation_id_created_at", "messages", ["conversation_id", "created_at"]
    )

    op.create_table(
        "agent_traces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_traces_run_id_created_at", "agent_traces", ["run_id", "created_at"])
    op.create_index("ix_agent_traces_message_id", "agent_traces", ["message_id"])
    op.create_index("ix_agent_traces_project_id_run_id", "agent_traces", ["project_id", "run_id"])

    op.create_table(
        "project_memory",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_project_memory_project_id_created_at", "project_memory", ["project_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_project_memory_project_id_created_at", table_name="project_memory")
    op.drop_table("project_memory")
    op.drop_index("ix_agent_traces_project_id_run_id", table_name="agent_traces")
    op.drop_index("ix_agent_traces_message_id", table_name="agent_traces")
    op.drop_index("ix_agent_traces_run_id_created_at", table_name="agent_traces")
    op.drop_table("agent_traces")
    op.drop_index("ix_messages_conversation_id_created_at", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_project_id_created_at", table_name="conversations")
    op.drop_table("conversations")
