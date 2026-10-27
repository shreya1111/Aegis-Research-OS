"""Graph edges table (design Phase 7 - knowledge graph).

Represents relationships between entities: co-authorship, citations, 
topic membership, institutional affiliations.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.graph_node import GraphNode
    from app.db.models.project import Project


class EdgeType(str, Enum):
    """Types of relationships in the knowledge graph."""
    
    CO_AUTHOR = "co_author"
    CITATION = "citation"
    TOPIC_MEMBERSHIP = "topic_membership"
    INSTITUTIONAL_AFFILIATION = "institutional_affiliation"


class GraphEdge(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Relationship edges in the knowledge graph.
    
    Connects nodes with typed relationships and optional weights
    for graph algorithms and visualization.
    """

    __tablename__ = "graph_edges"
    __table_args__ = (
        Index("ix_graph_edges_project_id", "project_id"),
        Index("ix_graph_edges_source_node_id", "source_node_id"),
        Index("ix_graph_edges_target_node_id", "target_node_id"),
        Index("ix_graph_edges_edge_type", "edge_type"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    edge_type: Mapped[EdgeType] = mapped_column(String(50), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    #: Additional edge properties: citation count, collaboration frequency, etc.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    # Relationships
    project: Mapped[Project] = relationship(back_populates="graph_edges")
    source_node: Mapped[GraphNode] = relationship(
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges"
    )
    target_node: Mapped[GraphNode] = relationship(
        foreign_keys=[target_node_id],
        back_populates="incoming_edges"
    )