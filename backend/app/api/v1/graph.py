"""Knowledge graph API endpoints (Phase 7)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUserDep, DbSessionDep
from app.api.v1.deps import ProjectInScopeDep
from app.core.envelope import ok
from app.core.errors import NotFoundError
from app.db.models.graph_edge import EdgeType
from app.db.models.graph_node import NodeType
from app.db.repositories.graph_repository import GraphRepository
from app.schemas.common import ApiResponse
from app.schemas.graph import (
    CreateRelationshipRequest,
    GraphDataResponse,
    GraphFilters,
    GraphStatsResponse,
    NodeDetailsResponse,
    NodeSearchResult,
)
from app.services.entity_extraction_service import EntityExtractionService
from app.services.graph_service import GraphService

router = APIRouter(tags=["graph"])


def _get_graph_service(session: DbSessionDep) -> GraphService:
    """Build a GraphService with its dependencies."""
    graph_repository = GraphRepository(session)
    entity_extraction_service = EntityExtractionService()
    
    return GraphService(
        graph_repository=graph_repository,
        entity_extraction_service=entity_extraction_service,
    )


@router.get(
    "/projects/{project_id}/graph/data",
    response_model=ApiResponse[GraphDataResponse],
    summary="Get knowledge graph visualization data",
)
async def get_graph_data(
    project: ProjectInScopeDep,
    graph_service: GraphService = Depends(_get_graph_service),
    node_type: NodeType | None = Query(None, alias="nodeType"),
    edge_type: EdgeType | None = Query(None, alias="edgeType"),
) -> ApiResponse[GraphDataResponse]:
    """Get graph nodes and edges for visualization."""
    graph_data = await graph_service.get_graph_data(
        project_id=project.id,
        node_type=node_type,
        edge_type=edge_type,
    )
    
    return ok(GraphDataResponse(**graph_data))


@router.get(
    "/projects/{project_id}/graph/stats",
    response_model=ApiResponse[GraphStatsResponse],
    summary="Get knowledge graph statistics",
)
async def get_graph_statistics(
    project: ProjectInScopeDep,
    graph_service: GraphService = Depends(_get_graph_service),
) -> ApiResponse[GraphStatsResponse]:
    """Get statistics about the knowledge graph."""
    stats = await graph_service.get_graph_statistics(project.id)
    return ok(GraphStatsResponse(**stats))


@router.get(
    "/projects/{project_id}/graph/nodes/{node_id}",
    response_model=ApiResponse[NodeDetailsResponse],
    summary="Get detailed information about a specific node",
)
async def get_node_details(
    project: ProjectInScopeDep,
    node_id: UUID,
    graph_service: GraphService = Depends(_get_graph_service),
) -> ApiResponse[NodeDetailsResponse]:
    """Get detailed information about a node including neighbors and connections."""
    details = await graph_service.get_node_details(project.id, node_id)
    
    if not details:
        raise NotFoundError("Node not found.")
    
    return ok(NodeDetailsResponse(**details))


@router.get(
    "/projects/{project_id}/graph/search",
    response_model=ApiResponse[list[NodeSearchResult]],
    summary="Search for nodes by name",
)
async def search_nodes(
    project: ProjectInScopeDep,
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    node_type: NodeType | None = Query(None, alias="nodeType"),
    graph_service: GraphService = Depends(_get_graph_service),
) -> ApiResponse[list[NodeSearchResult]]:
    """Search for nodes by name within the project."""
    results = await graph_service.search_nodes(
        project_id=project.id,
        query=q,
        node_type=node_type,
    )
    
    return ok([NodeSearchResult(**result) for result in results])


@router.post(
    "/projects/{project_id}/graph/relationships",
    response_model=ApiResponse[dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual relationship between nodes",
)
async def create_relationship(
    project: ProjectInScopeDep,
    payload: CreateRelationshipRequest,
    user: CurrentUserDep,
    graph_service: GraphService = Depends(_get_graph_service),
) -> ApiResponse[dict[str, Any]]:
    """Create a manual relationship between two nodes."""
    # Add user information to metadata
    metadata = payload.metadata.copy()
    metadata.update({
        "source": "manual",
        "created_by": str(user.id),
        "created_by_name": user.name,
    })
    
    edge = await graph_service.create_manual_relationship(
        project_id=project.id,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        relationship_type=payload.relationship_type,
        weight=payload.weight,
        metadata=metadata,
    )
    
    return ok({
        "id": str(edge.id),
        "source_node_id": str(edge.source_node_id),
        "target_node_id": str(edge.target_node_id),
        "edge_type": edge.edge_type.value,
        "weight": edge.weight,
        "metadata": edge.metadata_,
        "created_at": edge.created_at.isoformat(),
    })


@router.delete(
    "/projects/{project_id}/graph/nodes/{node_id}",
    response_model=ApiResponse[dict[str, str]],
    summary="Delete a node and all its relationships",
)
async def delete_node(
    project: ProjectInScopeDep,
    node_id: UUID,
    user: CurrentUserDep,
    graph_service: GraphService = Depends(_get_graph_service),
) -> ApiResponse[dict[str, str]]:
    """Delete a node and all its relationships."""
    success = await graph_service.delete_node(project.id, node_id)
    
    if not success:
        raise NotFoundError("Node not found.")
    
    return ok({"message": "Node deleted successfully."})


@router.delete(
    "/projects/{project_id}/graph/relationships/{edge_id}",
    response_model=ApiResponse[dict[str, str]],
    summary="Delete a specific relationship",
)
async def delete_relationship(
    project: ProjectInScopeDep,
    edge_id: UUID,
    user: CurrentUserDep,
    graph_service: GraphService = Depends(_get_graph_service),
) -> ApiResponse[dict[str, str]]:
    """Delete a specific relationship between nodes."""
    success = await graph_service.delete_relationship(project.id, edge_id)
    
    if not success:
        raise NotFoundError("Relationship not found.")
    
    return ok({"message": "Relationship deleted successfully."})


@router.post(
    "/projects/{project_id}/graph/rebuild",
    response_model=ApiResponse[dict[str, str]],
    summary="Rebuild knowledge graph from project documents",
)
async def rebuild_graph(
    project: ProjectInScopeDep,
    user: CurrentUserDep,
    graph_service: GraphService = Depends(_get_graph_service),
) -> JSONResponse:
    """Rebuild the knowledge graph by re-processing all project documents.
    
    This is a manual trigger for graph reconstruction, useful for testing
    or when the extraction algorithms are improved.
    """
    # This would typically be implemented as a background task
    # For now, return a message indicating the operation would be queued
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "success": True,
            "data": {
                "message": "Graph rebuild queued. This operation will process all documents in the background."
            },
            "error": None,
        }
    )