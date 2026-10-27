"""Add graph tables for Phase 7 knowledge graph

Revision ID: f3f6c804751d
Revises: fcaeaa760154
Create Date: 2026-08-30 13:43:55.834987

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'f3f6c804751d'
down_revision: str | Sequence[str] | None = 'fcaeaa760154'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create graph_nodes table
    op.create_table('graph_nodes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),  # 'author', 'topic', 'institution'
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('metadata', JSONB(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_graph_nodes_project_id'), 'graph_nodes', ['project_id'], unique=False)
    op.create_index(op.f('ix_graph_nodes_node_type'), 'graph_nodes', ['node_type'], unique=False)
    op.create_index(op.f('ix_graph_nodes_name'), 'graph_nodes', ['name'], unique=False)

    # Create graph_edges table  
    op.create_table('graph_edges',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('source_node_id', sa.Uuid(), nullable=False),
        sa.Column('target_node_id', sa.Uuid(), nullable=False),
        sa.Column('edge_type', sa.String(length=50), nullable=False),  # 'co_author', 'citation', 'topic_membership'
        sa.Column('weight', sa.Float(), nullable=False, default=1.0),
        sa.Column('metadata', JSONB(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_node_id'], ['graph_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['graph_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_graph_edges_project_id'), 'graph_edges', ['project_id'], unique=False)
    op.create_index(op.f('ix_graph_edges_source_node_id'), 'graph_edges', ['source_node_id'], unique=False)
    op.create_index(op.f('ix_graph_edges_target_node_id'), 'graph_edges', ['target_node_id'], unique=False)
    op.create_index(op.f('ix_graph_edges_edge_type'), 'graph_edges', ['edge_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_graph_edges_edge_type'), table_name='graph_edges')
    op.drop_index(op.f('ix_graph_edges_target_node_id'), table_name='graph_edges')
    op.drop_index(op.f('ix_graph_edges_source_node_id'), table_name='graph_edges')
    op.drop_index(op.f('ix_graph_edges_project_id'), table_name='graph_edges')
    op.drop_table('graph_edges')
    
    op.drop_index(op.f('ix_graph_nodes_name'), table_name='graph_nodes')
    op.drop_index(op.f('ix_graph_nodes_node_type'), table_name='graph_nodes')
    op.drop_index(op.f('ix_graph_nodes_project_id'), table_name='graph_nodes')
    op.drop_table('graph_nodes')
