"""Pydantic schemas for knowledge graph API (Phase 7)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.graph_edge import EdgeType
from app.db.models.graph_node import NodeType


class GraphNodeRead(BaseModel):
    """Schema for reading graph nodes."""
    
    id: UUID
    name: str
    node_type: NodeType = Field(alias="nodeType")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(alias="createdAt")
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class GraphEdgeRead(BaseModel):
    """Schema for reading graph edges."""
    
    id: UUID
    source_node_id: UUID = Field(alias="sourceNodeId")
    target_node_id: UUID = Field(alias="targetNodeId")
    edge_type: EdgeType = Field(alias="edgeType")
    weight: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(alias="createdAt")
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class GraphDataResponse(BaseModel):
    """Schema for graph visualization data."""
    
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class NodeDetailsResponse(BaseModel):
    """Schema for detailed node information."""
    
    node: dict[str, Any]
    neighbors: list[dict[str, Any]]
    connections: list[dict[str, Any]]


class GraphStatsResponse(BaseModel):
    """Schema for graph statistics."""
    
    total_nodes: int = Field(alias="totalNodes")
    total_edges: int = Field(alias="totalEdges")
    nodes_by_type: dict[str, int] = Field(alias="nodesByType")
    edges_by_type: dict[str, int] = Field(alias="edgesByType")
    
    model_config = {"populate_by_name": True}


class NodeSearchResult(BaseModel):
    """Schema for node search results."""
    
    id: UUID
    name: str
    type: NodeType
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateRelationshipRequest(BaseModel):
    """Schema for creating manual relationships."""
    
    source_node_id: UUID = Field(alias="sourceNodeId")
    target_node_id: UUID = Field(alias="targetNodeId")
    relationship_type: EdgeType = Field(alias="relationshipType")
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"populate_by_name": True}


class GraphFilters(BaseModel):
    """Schema for graph filtering options."""
    
    node_type: NodeType | None = Field(default=None, alias="nodeType")
    edge_type: EdgeType | None = Field(default=None, alias="edgeType")
    
    model_config = {"populate_by_name": True}