"""Integration tests for graph API endpoints (Phase 7).

Each test registers its own users through the public API and builds the state it
needs, matching the application-level fixture in :mod:`tests.conftest` (an
in-process ASGI client against a disposable database schema).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

PASSWORD = "correct-horse-battery"


async def _register_and_login(client: AsyncClient, *, email: str, name: str = "Test User") -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": name},
    )
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return str(response.json()["data"]["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_project(client: AsyncClient, token: str, title: str = "Graph project") -> str:
    response = await client.post("/api/v1/projects", json={"title": title}, headers=_auth(token))
    assert response.status_code == 201
    return str(response.json()["data"]["id"])


@pytest.mark.integration
async def test_get_graph_data_empty(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    response = await client.get(f"/api/v1/projects/{project_id}/graph/data", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == {"nodes": [], "edges": []}


@pytest.mark.integration
async def test_get_graph_stats_empty(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    response = await client.get(f"/api/v1/projects/{project_id}/graph/stats", headers=_auth(token))

    assert response.status_code == 200
    stats = response.json()["data"]
    assert stats["totalNodes"] == 0
    assert stats["totalEdges"] == 0
    assert stats["nodesByType"] == {}
    assert stats["edgesByType"] == {}


@pytest.mark.integration
async def test_search_nodes_empty(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    response = await client.get(
        f"/api/v1/projects/{project_id}/graph/search", params={"q": "smith"}, headers=_auth(token)
    )

    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.integration
async def test_get_nonexistent_node_details(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    response = await client.get(
        f"/api/v1/projects/{project_id}/graph/nodes/{uuid.uuid4()}", headers=_auth(token)
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "not found" in body["error"]["message"].lower()


@pytest.mark.integration
async def test_delete_nonexistent_node(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    response = await client.delete(
        f"/api/v1/projects/{project_id}/graph/nodes/{uuid.uuid4()}", headers=_auth(token)
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


@pytest.mark.integration
async def test_delete_nonexistent_relationship(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    response = await client.delete(
        f"/api/v1/projects/{project_id}/graph/relationships/{uuid.uuid4()}", headers=_auth(token)
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


@pytest.mark.integration
async def test_graph_rebuild_endpoint(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    response = await client.post(f"/api/v1/projects/{project_id}/graph/rebuild", headers=_auth(token))

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert "queued" in body["data"]["message"].lower()


@pytest.mark.integration
async def test_graph_data_with_filters(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    for params in (
        {"nodeType": "author"},
        {"edgeType": "co_author"},
        {"nodeType": "author", "edgeType": "co_author"},
    ):
        response = await client.get(
            f"/api/v1/projects/{project_id}/graph/data", params=params, headers=_auth(token)
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


@pytest.mark.integration
async def test_search_with_node_type_filter(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    response = await client.get(
        f"/api/v1/projects/{project_id}/graph/search",
        params={"q": "test", "nodeType": "author"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.integration
async def test_invalid_type_filters_are_rejected(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    invalid_node = await client.get(
        f"/api/v1/projects/{project_id}/graph/data",
        params={"nodeType": "invalid_type"},
        headers=_auth(token),
    )
    invalid_edge = await client.get(
        f"/api/v1/projects/{project_id}/graph/data",
        params={"edgeType": "invalid_type"},
        headers=_auth(token),
    )

    assert invalid_node.status_code == 422
    assert invalid_edge.status_code == 422


@pytest.mark.integration
async def test_create_relationship_validation(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)
    url = f"/api/v1/projects/{project_id}/graph/relationships"

    invalid_uuid = await client.post(
        url,
        json={
            "sourceNodeId": "invalid-uuid",
            "targetNodeId": str(uuid.uuid4()),
            "relationshipType": "co_author",
        },
        headers=_auth(token),
    )
    invalid_type = await client.post(
        url,
        json={
            "sourceNodeId": str(uuid.uuid4()),
            "targetNodeId": str(uuid.uuid4()),
            "relationshipType": "invalid_type",
        },
        headers=_auth(token),
    )
    negative_weight = await client.post(
        url,
        json={
            "sourceNodeId": str(uuid.uuid4()),
            "targetNodeId": str(uuid.uuid4()),
            "relationshipType": "co_author",
            "weight": -1.0,
        },
        headers=_auth(token),
    )

    assert invalid_uuid.status_code == 422
    assert invalid_type.status_code == 422
    assert negative_weight.status_code == 422


@pytest.mark.integration
async def test_search_validation(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    empty_query = await client.get(
        f"/api/v1/projects/{project_id}/graph/search", params={"q": ""}, headers=_auth(token)
    )
    missing_query = await client.get(
        f"/api/v1/projects/{project_id}/graph/search", headers=_auth(token)
    )

    assert empty_query.status_code == 422
    assert missing_query.status_code == 422


@pytest.mark.integration
async def test_unauthorized_access(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="graph@example.com")
    project_id = await _create_project(client, token)

    data = await client.get(f"/api/v1/projects/{project_id}/graph/data")
    stats = await client.get(f"/api/v1/projects/{project_id}/graph/stats")
    rebuild = await client.post(f"/api/v1/projects/{project_id}/graph/rebuild")

    assert data.status_code == 401
    assert stats.status_code == 401
    assert rebuild.status_code == 401


@pytest.mark.integration
async def test_cross_project_access_is_not_found(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    stranger = await _register_and_login(client, email="stranger@example.com", name="Stranger")
    project_id = await _create_project(client, owner)

    foreign = await client.get(
        f"/api/v1/projects/{project_id}/graph/data", headers=_auth(stranger)
    )
    missing = await client.get(
        f"/api/v1/projects/{uuid.uuid4()}/graph/data", headers=_auth(stranger)
    )

    assert foreign.status_code == 404
    assert missing.status_code == 404


@pytest.mark.integration
async def test_viewer_cannot_mutate_the_graph(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    viewer = await _register_and_login(client, email="viewer@example.com", name="Viewer")
    project_id = await _create_project(client, owner)
    invite = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=_auth(owner),
    )
    assert invite.status_code == 201

    rebuild = await client.post(f"/api/v1/projects/{project_id}/graph/rebuild", headers=_auth(viewer))
    delete = await client.delete(
        f"/api/v1/projects/{project_id}/graph/nodes/{uuid.uuid4()}", headers=_auth(viewer)
    )

    assert rebuild.status_code == 403
    assert delete.status_code == 403
