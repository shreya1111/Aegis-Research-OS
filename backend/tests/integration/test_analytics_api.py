"""Integration tests for analytics dataset authorization (Phase 8, design §9.3).

Dataset-scoped routes carry only the dataset id in the path, so authorisation
must resolve through the dataset's own project. These tests drive the public API
to prove a stranger cannot reach another project's data, and that an invited
viewer can read it but not mutate it.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

PASSWORD = "correct-horse-battery"


async def _register_and_login(client: AsyncClient, *, email: str, name: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": name},
    )
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return str(response.json()["data"]["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_project(client: AsyncClient, token: str) -> str:
    response = await client.post("/api/v1/projects", json={"title": "Analytics"}, headers=_auth(token))
    assert response.status_code == 201
    return str(response.json()["data"]["id"])


async def _invite(client: AsyncClient, token: str, project_id: str, email: str, role: str) -> None:
    response = await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"email": email, "role": role},
        headers=_auth(token),
    )
    assert response.status_code == 201


async def _upload_dataset(client: AsyncClient, token: str, project_id: str) -> str:
    response = await client.post(
        f"/api/v1/projects/{project_id}/analytics/datasets",
        files={"file": ("data.csv", b"group,value\na,1\nb,2\n", "text/csv")},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


@pytest.mark.integration
async def test_stranger_cannot_reach_another_projects_dataset(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    stranger = await _register_and_login(client, email="stranger@example.com", name="Stranger")
    project_id = await _create_project(client, owner)
    dataset_id = await _upload_dataset(client, owner, project_id)

    read = await client.get(f"/api/v1/analytics/datasets/{dataset_id}", headers=_auth(stranger))
    analyses = await client.get(
        f"/api/v1/analytics/datasets/{dataset_id}/analyses", headers=_auth(stranger)
    )
    analyze = await client.post(
        f"/api/v1/analytics/datasets/{dataset_id}/analyze",
        json={"question": "What is the mean value?"},
        headers=_auth(stranger),
    )
    delete = await client.delete(
        f"/api/v1/analytics/datasets/{dataset_id}", headers=_auth(stranger)
    )
    owners_view = await client.get(
        f"/api/v1/analytics/datasets/{dataset_id}", headers=_auth(owner)
    )

    assert read.status_code == 404
    assert analyses.status_code == 404
    assert analyze.status_code == 404
    assert delete.status_code == 404, "a stranger must not be able to delete another project's data"
    assert owners_view.status_code == 200, "the owner still reaches their dataset"


@pytest.mark.integration
async def test_viewer_can_read_but_not_mutate_datasets(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    viewer = await _register_and_login(client, email="viewer@example.com", name="Viewer")
    project_id = await _create_project(client, owner)
    await _invite(client, owner, project_id, "viewer@example.com", "viewer")
    dataset_id = await _upload_dataset(client, owner, project_id)

    read = await client.get(f"/api/v1/analytics/datasets/{dataset_id}", headers=_auth(viewer))
    analyses = await client.get(
        f"/api/v1/analytics/datasets/{dataset_id}/analyses", headers=_auth(viewer)
    )
    analyze = await client.post(
        f"/api/v1/analytics/datasets/{dataset_id}/analyze",
        json={"question": "What is the mean value?"},
        headers=_auth(viewer),
    )
    delete = await client.delete(
        f"/api/v1/analytics/datasets/{dataset_id}", headers=_auth(viewer)
    )
    owners_delete = await client.delete(
        f"/api/v1/analytics/datasets/{dataset_id}", headers=_auth(owner)
    )

    assert read.status_code == 200
    assert analyses.status_code == 200
    assert analyze.status_code == 403
    assert delete.status_code == 403
    assert owners_delete.status_code == 200
