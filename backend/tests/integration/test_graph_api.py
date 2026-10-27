"""Integration tests for graph API endpoints (Phase 7)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.models.graph_edge import EdgeType
from app.db.models.graph_node import NodeType


@pytest.mark.integration
async def test_get_graph_data_empty(auth_client: TestClient, test_project_id: str) -> None:
    """Test getting graph data for a project with no entities."""
    response = auth_client.get(f"/api/v1/projects/{test_project_id}/graph/data")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["nodes"] == []
    assert data["data"]["edges"] == []


@pytest.mark.integration
async def test_get_graph_stats_empty(auth_client: TestClient, test_project_id: str) -> None:
    """Test getting graph statistics for empty graph."""
    response = auth_client.get(f"/api/v1/projects/{test_project_id}/graph/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    stats = data["data"]
    assert stats["totalNodes"] == 0
    assert stats["totalEdges"] == 0
    assert stats["nodesByType"] == {}
    assert stats["edgesByType"] == {}


@pytest.mark.integration
async def test_search_nodes_empty(auth_client: TestClient, test_project_id: str) -> None:
    """Test searching nodes in empty graph."""
    response = auth_client.get(
        f"/api/v1/projects/{test_project_id}/graph/search",
        params={"q": "smith"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"] == []


@pytest.mark.integration 
async def test_get_nonexistent_node_details(auth_client: TestClient, test_project_id: str) -> None:
    """Test getting details for non-existent node."""
    fake_node_id = str(uuid.uuid4())
    response = auth_client.get(
        f"/api/v1/projects/{test_project_id}/graph/nodes/{fake_node_id}"
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"]["message"].lower()


@pytest.mark.integration
async def test_delete_nonexistent_node(auth_client: TestClient, test_project_id: str) -> None:
    """Test deleting non-existent node."""
    fake_node_id = str(uuid.uuid4())
    response = auth_client.delete(
        f"/api/v1/projects/{test_project_id}/graph/nodes/{fake_node_id}"
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False


@pytest.mark.integration
async def test_delete_nonexistent_relationship(auth_client: TestClient, test_project_id: str) -> None:
    """Test deleting non-existent relationship."""
    fake_edge_id = str(uuid.uuid4())
    response = auth_client.delete(
        f"/api/v1/projects/{test_project_id}/graph/relationships/{fake_edge_id}"
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False


@pytest.mark.integration
async def test_graph_rebuild_endpoint(auth_client: TestClient, test_project_id: str) -> None:
    """Test graph rebuild endpoint."""
    response = auth_client.post(f"/api/v1/projects/{test_project_id}/graph/rebuild")
    
    assert response.status_code == 202
    data = response.json()
    assert data["success"] is True
    assert "queued" in data["data"]["message"].lower()


@pytest.mark.integration
async def test_graph_data_with_filters(auth_client: TestClient, test_project_id: str) -> None:
    """Test getting graph data with node/edge type filters."""
    # Test with node type filter
    response = auth_client.get(
        f"/api/v1/projects/{test_project_id}/graph/data",
        params={"nodeType": "author"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Test with edge type filter
    response = auth_client.get(
        f"/api/v1/projects/{test_project_id}/graph/data", 
        params={"edgeType": "co_author"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Test with both filters
    response = auth_client.get(
        f"/api/v1/projects/{test_project_id}/graph/data",
        params={"nodeType": "author", "edgeType": "co_author"}
    )
    
    assert response.status_code == 200
    data = response.json() 
    assert data["success"] is True


@pytest.mark.integration
async def test_search_with_node_type_filter(auth_client: TestClient, test_project_id: str) -> None:
    """Test searching with node type filter."""
    response = auth_client.get(
        f"/api/v1/projects/{test_project_id}/graph/search",
        params={"q": "test", "nodeType": "author"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.integration
async def test_invalid_node_type_filter(auth_client: TestClient, test_project_id: str) -> None:
    """Test invalid node type filter."""
    response = auth_client.get(
        f"/api/v1/projects/{test_project_id}/graph/data",
        params={"nodeType": "invalid_type"}
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.integration
async def test_invalid_edge_type_filter(auth_client: TestClient, test_project_id: str) -> None:
    """Test invalid edge type filter.""" 
    response = auth_client.get(
        f"/api/v1/projects/{test_project_id}/graph/data",
        params={"edgeType": "invalid_type"}
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.integration
async def test_create_relationship_validation(auth_client: TestClient, test_project_id: str) -> None:
    """Test relationship creation validation."""
    # Test with invalid UUIDs
    response = auth_client.post(
        f"/api/v1/projects/{test_project_id}/graph/relationships",
        json={
            "sourceNodeId": "invalid-uuid",
            "targetNodeId": str(uuid.uuid4()),
            "relationshipType": "co_author",
        }
    )
    
    assert response.status_code == 422  # Validation error
    
    # Test with invalid relationship type
    response = auth_client.post(
        f"/api/v1/projects/{test_project_id}/graph/relationships",
        json={
            "sourceNodeId": str(uuid.uuid4()),
            "targetNodeId": str(uuid.uuid4()),
            "relationshipType": "invalid_type",
        }
    )
    
    assert response.status_code == 422  # Validation error
    
    # Test with invalid weight
    response = auth_client.post(
        f"/api/v1/projects/{test_project_id}/graph/relationships",
        json={
            "sourceNodeId": str(uuid.uuid4()),
            "targetNodeId": str(uuid.uuid4()),
            "relationshipType": "co_author",
            "weight": -1.0,  # Negative weight should be invalid
        }
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.integration
async def test_search_validation(auth_client: TestClient, test_project_id: str) -> None:
    """Test search query validation."""
    # Test empty query
    response = auth_client.get(
        f"/api/v1/projects/{test_project_id}/graph/search",
        params={"q": ""}
    )
    
    assert response.status_code == 422  # Validation error
    
    # Test missing query parameter
    response = auth_client.get(f"/api/v1/projects/{test_project_id}/graph/search")
    
    assert response.status_code == 422  # Validation error


@pytest.mark.integration
async def test_unauthorized_access(client: TestClient, test_project_id: str) -> None:
    """Test accessing graph endpoints without authentication."""
    # Test without auth token
    response = client.get(f"/api/v1/projects/{test_project_id}/graph/data")
    assert response.status_code == 401
    
    response = client.get(f"/api/v1/projects/{test_project_id}/graph/stats")
    assert response.status_code == 401
    
    response = client.post(f"/api/v1/projects/{test_project_id}/graph/rebuild")
    assert response.status_code == 401


@pytest.mark.integration
async def test_cross_project_access(
    auth_client: TestClient, 
    test_project_id: str,
    db_session,
    test_user,
) -> None:
    """Test that users cannot access other users' project graphs.""" 
    # This would require creating another user and project
    # For now, just test with a random project ID
    fake_project_id = str(uuid.uuid4())
    
    response = auth_client.get(f"/api/v1/projects/{fake_project_id}/graph/data")
    assert response.status_code == 404  # Project not found or no access