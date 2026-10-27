"""Graph service for managing knowledge graph operations (Phase 7)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.models.graph_edge import EdgeType, GraphEdge
from app.db.models.graph_node import GraphNode, NodeType
from app.db.repositories.graph_repository import GraphRepository
from app.services.entity_extraction_service import (
    EntityExtractionResult,
    EntityExtractionService,
    ExtractedEntity,
    ExtractedRelationship,
)
from app.services.ingestion.types import ExtractedDocument
from app.services.retrieval.types import RetrievedChunk

logger = get_logger(__name__)


class GraphService:
    """Business logic for knowledge graph construction and querying."""

    def __init__(
        self,
        *,
        graph_repository: GraphRepository,
        entity_extraction_service: EntityExtractionService,
    ) -> None:
        self._graph_repo = graph_repository
        self._extraction_service = entity_extraction_service

    async def process_document_entities(
        self, 
        project_id: UUID, 
        document: ExtractedDocument
    ) -> None:
        """Extract entities from a document and add them to the knowledge graph."""
        logger.info(
            "graph.process_document_entities.start",
            extra={
                "event": "graph.process_document_entities.start",
                "project_id": str(project_id),
                "document_title": document.title or "Unknown",
            }
        )
        
        try:
            # Extract entities and relationships
            extraction_result = self._extraction_service.extract_from_document(document)
            
            # Deduplicate entities
            unique_entities = self._extraction_service.deduplicate_entities(
                list(extraction_result.entities)
            )
            
            # Create or update nodes
            entity_to_node = {}
            for entity in unique_entities:
                node = await self._graph_repo.get_or_create_node(
                    project_id=project_id,
                    node_type=entity.entity_type,
                    name=entity.name,
                    metadata=entity.metadata,
                )
                entity_to_node[entity] = node
            
            # Create relationships
            for relationship in extraction_result.relationships:
                source_node = entity_to_node.get(relationship.source)
                target_node = entity_to_node.get(relationship.target)
                
                if source_node and target_node:
                    await self._graph_repo.get_or_create_edge(
                        project_id=project_id,
                        source_node_id=source_node.id,
                        target_node_id=target_node.id,
                        edge_type=relationship.relationship_type,
                        weight=relationship.weight,
                        metadata=relationship.metadata,
                    )
            
            logger.info(
                "graph.process_document_entities.success",
                extra={
                    "event": "graph.process_document_entities.success",
                    "project_id": str(project_id),
                    "entities_processed": len(unique_entities),
                    "relationships_created": len(extraction_result.relationships),
                }
            )
            
        except Exception:
            logger.exception(
                "graph.process_document_entities.failed",
                extra={
                    "event": "graph.process_document_entities.failed",
                    "project_id": str(project_id),
                }
            )
            raise

    async def process_retrieval_entities(
        self, 
        project_id: UUID, 
        chunks: list[RetrievedChunk]
    ) -> None:
        """Extract entities from retrieval results and add to knowledge graph."""
        logger.info(
            "graph.process_retrieval_entities.start",
            extra={
                "event": "graph.process_retrieval_entities.start",
                "project_id": str(project_id),
                "chunk_count": len(chunks),
            }
        )
        
        try:
            # Extract entities from chunks
            extraction_result = self._extraction_service.extract_from_retrieved_chunks(chunks)
            
            # Deduplicate entities
            unique_entities = self._extraction_service.deduplicate_entities(
                list(extraction_result.entities)
            )
            
            # Create or update nodes
            for entity in unique_entities:
                await self._graph_repo.get_or_create_node(
                    project_id=project_id,
                    node_type=entity.entity_type,
                    name=entity.name,
                    metadata=entity.metadata,
                )
            
            logger.info(
                "graph.process_retrieval_entities.success",
                extra={
                    "event": "graph.process_retrieval_entities.success",
                    "project_id": str(project_id),
                    "entities_processed": len(unique_entities),
                }
            )
            
        except Exception:
            logger.exception(
                "graph.process_retrieval_entities.failed",
                extra={
                    "event": "graph.process_retrieval_entities.failed",
                    "project_id": str(project_id),
                }
            )
            raise

    async def get_graph_data(
        self,
        project_id: UUID,
        node_type: NodeType | None = None,
        edge_type: EdgeType | None = None
    ) -> dict[str, Any]:
        """Get graph data formatted for frontend visualization."""
        nodes = await self._graph_repo.get_nodes_for_project(
            project_id, node_type=node_type
        )
        edges = await self._graph_repo.get_edges_for_project(
            project_id, edge_type=edge_type
        )
        
        # Format for frontend (react-flow compatible)
        formatted_nodes = []
        for node in nodes:
            formatted_nodes.append({
                "id": str(node.id),
                "type": node.node_type.value,
                "data": {
                    "label": node.name,
                    "nodeType": node.node_type.value,
                    "metadata": node.metadata_,
                    "createdAt": node.created_at.isoformat(),
                },
                "position": {"x": 0, "y": 0},  # Will be positioned by layout algorithm
            })
        
        formatted_edges = []
        for edge in edges:
            formatted_edges.append({
                "id": str(edge.id),
                "source": str(edge.source_node_id),
                "target": str(edge.target_node_id),
                "type": edge.edge_type.value,
                "data": {
                    "weight": edge.weight,
                    "edgeType": edge.edge_type.value,
                    "metadata": edge.metadata_,
                    "createdAt": edge.created_at.isoformat(),
                },
            })
        
        return {
            "nodes": formatted_nodes,
            "edges": formatted_edges,
        }

    async def get_node_details(self, project_id: UUID, node_id: UUID) -> dict[str, Any] | None:
        """Get detailed information about a specific node."""
        node = await self._graph_repo.get_node_by_id(node_id, project_id)
        if not node:
            return None
        
        neighbors, connecting_edges = await self._graph_repo.get_node_neighbors(
            node_id, project_id
        )
        
        return {
            "node": {
                "id": str(node.id),
                "name": node.name,
                "type": node.node_type.value,
                "metadata": node.metadata_,
                "createdAt": node.created_at.isoformat(),
            },
            "neighbors": [
                {
                    "id": str(neighbor.id),
                    "name": neighbor.name,
                    "type": neighbor.node_type.value,
                }
                for neighbor in neighbors
            ],
            "connections": [
                {
                    "id": str(edge.id),
                    "type": edge.edge_type.value,
                    "weight": edge.weight,
                    "sourceId": str(edge.source_node_id),
                    "targetId": str(edge.target_node_id),
                    "metadata": edge.metadata_,
                }
                for edge in connecting_edges
            ],
        }

    async def get_graph_statistics(self, project_id: UUID) -> dict[str, Any]:
        """Get statistics about the knowledge graph."""
        return await self._graph_repo.get_graph_stats(project_id)

    async def search_nodes(
        self,
        project_id: UUID,
        query: str,
        node_type: NodeType | None = None
    ) -> list[dict[str, Any]]:
        """Search for nodes by name."""
        nodes = await self._graph_repo.search_nodes(
            project_id, query, node_type=node_type
        )
        
        return [
            {
                "id": str(node.id),
                "name": node.name,
                "type": node.node_type.value,
                "metadata": node.metadata_,
            }
            for node in nodes
        ]

    async def create_manual_relationship(
        self,
        project_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        relationship_type: EdgeType,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None
    ) -> GraphEdge:
        """Create a manual relationship between two nodes."""
        return await self._graph_repo.get_or_create_edge(
            project_id=project_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=relationship_type,
            weight=weight,
            metadata=metadata or {"source": "manual"},
        )

    async def delete_node(self, project_id: UUID, node_id: UUID) -> bool:
        """Delete a node and all its relationships."""
        return await self._graph_repo.delete_node(node_id, project_id)

    async def delete_relationship(self, project_id: UUID, edge_id: UUID) -> bool:
        """Delete a specific relationship."""
        return await self._graph_repo.delete_edge(edge_id, project_id)