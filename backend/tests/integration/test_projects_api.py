"""Integration tests for the ``/projects`` router (FR-B, design §9.3)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, *, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery", "name": "Test User"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery"},
    )
    return str(response.json()["data"]["access_token"])


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
async def test_create_project_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/api/v1/projects", json={"title": "Thesis"})

    assert response.status_code == 401


@pytest.mark.integration
async def test_create_project_returns_the_created_workspace(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="alice@example.com")

    response = await client.post(
        "/api/v1/projects",
        json={"title": "My Thesis", "description": "Literature review"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "My Thesis"
    assert data["description"] == "Literature review"
    assert data["id"]
    assert data["created_at"]


@pytest.mark.integration
async def test_create_project_allows_an_omitted_description(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="alice@example.com")

    response = await client.post(
        "/api/v1/projects", json={"title": "My Thesis"}, headers=_auth_headers(token)
    )

    assert response.status_code == 201
    assert response.json()["data"]["description"] is None


@pytest.mark.integration
async def test_create_project_rejects_an_empty_title(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="alice@example.com")

    response = await client.post(
        "/api/v1/projects", json={"title": ""}, headers=_auth_headers(token)
    )

    assert response.status_code == 422


@pytest.mark.integration
async def test_list_projects_returns_only_the_callers_projects(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, email="alice@example.com")
    bob_token = await _register_and_login(client, email="bob@example.com")

    await client.post(
        "/api/v1/projects", json={"title": "Alice's project"}, headers=_auth_headers(alice_token)
    )
    await client.post(
        "/api/v1/projects", json={"title": "Bob's project"}, headers=_auth_headers(bob_token)
    )

    response = await client.get("/api/v1/projects", headers=_auth_headers(alice_token))

    body = response.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Alice's project"


@pytest.mark.integration
async def test_list_projects_orders_most_recent_first(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="alice@example.com")
    for title in ["First", "Second", "Third"]:
        await client.post("/api/v1/projects", json={"title": title}, headers=_auth_headers(token))

    response = await client.get("/api/v1/projects", headers=_auth_headers(token))

    titles = [item["title"] for item in response.json()["data"]["items"]]
    assert titles == ["Third", "Second", "First"]


@pytest.mark.integration
async def test_list_projects_paginates(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="alice@example.com")
    for index in range(3):
        await client.post(
            "/api/v1/projects", json={"title": f"Project {index}"}, headers=_auth_headers(token)
        )

    response = await client.get(
        "/api/v1/projects", params={"page": 1, "page_size": 2}, headers=_auth_headers(token)
    )

    body = response.json()["data"]
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2


@pytest.mark.integration
async def test_get_project_returns_the_owners_workspace(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="alice@example.com")
    created = await client.post(
        "/api/v1/projects", json={"title": "My Thesis"}, headers=_auth_headers(token)
    )
    project_id = created.json()["data"]["id"]

    response = await client.get(f"/api/v1/projects/{project_id}", headers=_auth_headers(token))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == project_id


@pytest.mark.integration
async def test_get_project_for_another_owner_returns_404_not_403(client: AsyncClient) -> None:
    """Cross-tenant access must be indistinguishable from a missing resource
    (design §6.3, FR-B3)."""
    alice_token = await _register_and_login(client, email="alice@example.com")
    bob_token = await _register_and_login(client, email="bob@example.com")
    created = await client.post(
        "/api/v1/projects",
        json={"title": "Alice's private project"},
        headers=_auth_headers(alice_token),
    )
    project_id = created.json()["data"]["id"]

    response = await client.get(f"/api/v1/projects/{project_id}", headers=_auth_headers(bob_token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.integration
async def test_get_a_nonexistent_project_returns_the_same_error_shape(
    client: AsyncClient,
) -> None:
    alice_token = await _register_and_login(client, email="alice@example.com")
    bob_token = await _register_and_login(client, email="bob@example.com")
    created = await client.post(
        "/api/v1/projects",
        json={"title": "Alice's private project"},
        headers=_auth_headers(alice_token),
    )
    real_project_id = created.json()["data"]["id"]
    fake_project_id = "00000000-0000-0000-0000-000000000000"

    cross_tenant = await client.get(
        f"/api/v1/projects/{real_project_id}", headers=_auth_headers(bob_token)
    )
    nonexistent = await client.get(
        f"/api/v1/projects/{fake_project_id}", headers=_auth_headers(bob_token)
    )

    assert cross_tenant.status_code == nonexistent.status_code == 404
    assert cross_tenant.json()["error"] == nonexistent.json()["error"]


@pytest.mark.integration
async def test_delete_project_removes_it_for_the_owner(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="alice@example.com")
    created = await client.post(
        "/api/v1/projects", json={"title": "Disposable"}, headers=_auth_headers(token)
    )
    project_id = created.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/projects/{project_id}", headers=_auth_headers(token)
    )
    get_response = await client.get(f"/api/v1/projects/{project_id}", headers=_auth_headers(token))

    assert delete_response.status_code == 200
    assert get_response.status_code == 404


@pytest.mark.integration
async def test_delete_project_by_another_owner_returns_404_and_does_not_delete(
    client: AsyncClient,
) -> None:
    alice_token = await _register_and_login(client, email="alice@example.com")
    bob_token = await _register_and_login(client, email="bob@example.com")
    created = await client.post(
        "/api/v1/projects",
        json={"title": "Alice's private project"},
        headers=_auth_headers(alice_token),
    )
    project_id = created.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/projects/{project_id}", headers=_auth_headers(bob_token)
    )
    get_response = await client.get(
        f"/api/v1/projects/{project_id}", headers=_auth_headers(alice_token)
    )

    assert delete_response.status_code == 404
    assert get_response.status_code == 200


@pytest.mark.integration
async def test_full_registration_login_project_lifecycle(client: AsyncClient) -> None:
    """End-to-end happy path matching the Phase 1 acceptance criterion:
    a user can register, log in, create a project, and see it listed."""
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "correct-horse-battery", "name": "Carol"},
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "correct-horse-battery"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["data"]["access_token"]

    create_response = await client.post(
        "/api/v1/projects",
        json={"title": "Carol's Research", "description": "PhD literature review"},
        headers=_auth_headers(token),
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["data"]["id"]

    list_response = await client.get("/api/v1/projects", headers=_auth_headers(token))
    assert list_response.status_code == 200
    listed_ids = [item["id"] for item in list_response.json()["data"]["items"]]
    assert project_id in listed_ids

    workspace_response = await client.get(
        f"/api/v1/projects/{project_id}", headers=_auth_headers(token)
    )
    assert workspace_response.status_code == 200
    assert workspace_response.json()["data"]["title"] == "Carol's Research"
