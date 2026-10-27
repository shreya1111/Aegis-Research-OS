"""Graph nodes table (design Phase 7 - knowledge graph).

Represents entities extracted from documents and external sources:
authors, topics, institutions with their metadata and relationships.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.graph_edge import GraphEdge
    from app.db.models.project import Project


class NodeType(str, Enum):
    """Types of entities in the knowledge graph."""
    
    AUTHOR = "author"
    TOPIC = "topic" 
    INSTITUTION = "institution"


class GraphNode(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Entity nodes in the knowledge graph.
    
    Represents authors, topics, and institutions extracted from documents
    and external sources, with metadata for display and relationships.
    """

    __tablename__ = "graph_nodes"
    __table_args__ = (
        Index("ix_graph_nodes_project_id", "project_id"),
        Index("ix_graph_nodes_node_type", "node_type"),
        Index("ix_graph_nodes_name", "name"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_type: Mapped[NodeType] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    #: Additional node properties: affiliation, ORCID, topic keywords, etc.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    # Relationships
    project: Mapped[Project] = relationship(back_populates="graph_nodes")
    outgoing_edges: Mapped[list[GraphEdge]] = relationship(
        foreign_keys="GraphEdge.source_node_id",
        back_populates="source_node"
    )
    incoming_edges: Mapped[list[GraphEdge]] = relationship(
        foreign_keys="GraphEdge.target_node_id", 
        back_populates="target_node"
    )