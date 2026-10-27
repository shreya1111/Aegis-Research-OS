"""Repository for graph nodes and edges (Phase 7 knowledge graph)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.graph_edge import EdgeType, GraphEdge
from app.db.models.graph_node import GraphNode, NodeType


class GraphRepository:
    """Data access layer for knowledge graph nodes and edges."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_node(
        self,
        *,
        project_id: UUID,
        node_type: NodeType,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> GraphNode:
        """Create a new graph node."""
        node = GraphNode(
            project_id=project_id,
            node_type=node_type,
            name=name,
            metadata_=metadata or {},
        )
        self._session.add(node)
        await self._session.commit()
        await self._session.refresh(node)
        return node

    async def get_or_create_node(
        self,
        *,
        project_id: UUID,
        node_type: NodeType,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> GraphNode:
        """Get existing node or create if not exists."""
        # Try to find existing node by name and type within project
        stmt = select(GraphNode).where(
            GraphNode.project_id == project_id,
            GraphNode.node_type == node_type,
            func.lower(GraphNode.name) == name.lower()
        )
        result = await self._session.execute(stmt)
        existing_node = result.scalar_one_or_none()
        
        if existing_node:
            # Update metadata if provided
            if metadata:
                existing_node.metadata_.update(metadata)
                await self._session.commit()
            return existing_node
        
        # Create new node
        return await self.create_node(
            project_id=project_id,
            node_type=node_type,
            name=name,
            metadata=metadata,
        )

    async def create_edge(
        self,
        *,
        project_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        edge_type: EdgeType,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> GraphEdge:
        """Create a new graph edge."""
        edge = GraphEdge(
            project_id=project_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            weight=weight,
            metadata_=metadata or {},
        )
        self._session.add(edge)
        await self._session.commit()
        await self._session.refresh(edge)
        return edge

    async def get_or_create_edge(
        self,
        *,
        project_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        edge_type: EdgeType,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> GraphEdge:
        """Get existing edge or create if not exists."""
        # Check for existing edge
        stmt = select(GraphEdge).where(
            GraphEdge.project_id == project_id,
            GraphEdge.source_node_id == source_node_id,
            GraphEdge.target_node_id == target_node_id,
            GraphEdge.edge_type == edge_type,
        )
        result = await self._session.execute(stmt)
        existing_edge = result.scalar_one_or_none()
        
        if existing_edge:
            # Update weight and metadata
            existing_edge.weight = max(existing_edge.weight, weight)
            if metadata:
                existing_edge.metadata_.update(metadata)
            await self._session.commit()
            return existing_edge
        
        return await self.create_edge(
            project_id=project_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            weight=weight,
            metadata=metadata,
        )

    async def get_nodes_for_project(
        self, 
        project_id: UUID,
        node_type: NodeType | None = None,
        limit: int = 100
    ) -> list[GraphNode]:
        """Get all nodes for a project, optionally filtered by type."""
        stmt = select(GraphNode).where(GraphNode.project_id == project_id)
        
        if node_type:
            stmt = stmt.where(GraphNode.node_type == node_type)
        
        stmt = stmt.order_by(GraphNode.name).limit(limit)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_edges_for_project(
        self, 
        project_id: UUID,
        edge_type: EdgeType | None = None,
        limit: int = 200
    ) -> list[GraphEdge]:
        """Get all edges for a project, optionally filtered by type."""
        stmt = (
            select(GraphEdge)
            .options(
                selectinload(GraphEdge.source_node),
                selectinload(GraphEdge.target_node)
            )
            .where(GraphEdge.project_id == project_id)
        )
        
        if edge_type:
            stmt = stmt.where(GraphEdge.edge_type == edge_type)
        
        stmt = stmt.order_by(GraphEdge.weight.desc()).limit(limit)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_node_by_id(self, node_id: UUID, project_id: UUID) -> GraphNode | None:
        """Get a specific node by ID within a project."""
        stmt = select(GraphNode).where(
            GraphNode.id == node_id,
            GraphNode.project_id == project_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_node_neighbors(
        self, 
        node_id: UUID, 
        project_id: UUID
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Get all neighboring nodes and connecting edges for a given node."""
        # Get outgoing edges
        outgoing_stmt = (
            select(GraphEdge)
            .options(selectinload(GraphEdge.target_node))
            .where(
                GraphEdge.source_node_id == node_id,
                GraphEdge.project_id == project_id
            )
        )
        
        # Get incoming edges  
        incoming_stmt = (
            select(GraphEdge)
            .options(selectinload(GraphEdge.source_node))
            .where(
                GraphEdge.target_node_id == node_id,
                GraphEdge.project_id == project_id
            )
        )
        
        outgoing_result = await self._session.execute(outgoing_stmt)
        incoming_result = await self._session.execute(incoming_stmt)
        
        outgoing_edges = list(outgoing_result.scalars().all())
        incoming_edges = list(incoming_result.scalars().all())
        
        # Collect unique neighboring nodes
        neighbors = set()
        all_edges = outgoing_edges + incoming_edges
        
        for edge in outgoing_edges:
            neighbors.add(edge.target_node)
        for edge in incoming_edges:
            neighbors.add(edge.source_node)
        
        return list(neighbors), all_edges

    async def get_graph_stats(self, project_id: UUID) -> dict[str, Any]:
        """Get basic statistics about the knowledge graph."""
        # Count nodes by type
        node_counts_stmt = (
            select(GraphNode.node_type, func.count(GraphNode.id))
            .where(GraphNode.project_id == project_id)
            .group_by(GraphNode.node_type)
        )
        
        # Count edges by type
        edge_counts_stmt = (
            select(GraphEdge.edge_type, func.count(GraphEdge.id))
            .where(GraphEdge.project_id == project_id)
            .group_by(GraphEdge.edge_type)
        )
        
        node_result = await self._session.execute(node_counts_stmt)
        edge_result = await self._session.execute(edge_counts_stmt)
        
        node_counts = dict(node_result.all())
        edge_counts = dict(edge_result.all())
        
        return {
            "total_nodes": sum(node_counts.values()),
            "total_edges": sum(edge_counts.values()),
            "nodes_by_type": node_counts,
            "edges_by_type": edge_counts,
        }

    async def search_nodes(
        self,
        project_id: UUID,
        query: str,
        node_type: NodeType | None = None,
        limit: int = 20
    ) -> list[GraphNode]:
        """Search for nodes by name within a project."""
        stmt = select(GraphNode).where(
            GraphNode.project_id == project_id,
            func.lower(GraphNode.name).contains(query.lower())
        )
        
        if node_type:
            stmt = stmt.where(GraphNode.node_type == node_type)
        
        stmt = stmt.order_by(GraphNode.name).limit(limit)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_node(self, node_id: UUID, project_id: UUID) -> bool:
        """Delete a node and all its edges."""
        stmt = select(GraphNode).where(
            GraphNode.id == node_id,
            GraphNode.project_id == project_id
        )
        result = await self._session.execute(stmt)
        node = result.scalar_one_or_none()
        
        if not node:
            return False
        
        await self._session.delete(node)
        await self._session.commit()
        return True

    async def delete_edge(self, edge_id: UUID, project_id: UUID) -> bool:
        """Delete a specific edge."""
        stmt = select(GraphEdge).where(
            GraphEdge.id == edge_id,
            GraphEdge.project_id == project_id
        )
        result = await self._session.execute(stmt)
        edge = result.scalar_one_or_none()
        
        if not edge:
            return False
        
        await self._session.delete(edge)
        await self._session.commit()
        return True