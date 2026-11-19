"""Integration tests for reports and export (Phase 6, 9, 10).

Report generation runs on the deterministic mock agent, and background tasks run
inside the in-process ASGI call, so a ``POST`` returns after generation finished.
Tests drive the public API so they cover roles, tenancy, and the envelope.
"""

from __future__ import annotations

import io

import pytest
from docx import Document
from httpx import AsyncClient

PASSWORD = "correct-horse-battery"


async def _register_and_login(client: AsyncClient, *, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "name": "Test User"},
    )
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return str(response.json()["data"]["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_project(client: AsyncClient, token: str) -> str:
    response = await client.post(
        "/api/v1/projects", json={"title": "Reports project"}, headers=_auth(token)
    )
    assert response.status_code == 201
    return str(response.json()["data"]["id"])


async def _create_report(
    client: AsyncClient, token: str, project_id: str, title: str = "Transformers survey"
) -> str:
    response = await client.post(
        f"/api/v1/projects/{project_id}/reports",
        json={"type": "literature_review", "title": title},
        headers=_auth(token),
    )
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "pending"
    return str(response.json()["data"]["id"])


@pytest.mark.integration
async def test_report_is_generated_and_listed(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="owner@example.com")
    project_id = await _create_project(client, token)

    report_id = await _create_report(client, token, project_id)

    detail = await client.get(f"/api/v1/reports/{report_id}", headers=_auth(token))
    listing = await client.get(f"/api/v1/projects/{project_id}/reports", headers=_auth(token))

    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["status"] == "completed"
    assert data["content_markdown"]
    assert [item["id"] for item in listing.json()["data"]] == [report_id]


@pytest.mark.integration
async def test_report_generation_is_recorded_in_the_activity_log(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="owner@example.com")
    project_id = await _create_project(client, token)
    await _create_report(client, token, project_id)

    response = await client.get(f"/api/v1/projects/{project_id}/activity", headers=_auth(token))

    assert response.status_code == 200
    assert "report" in response.text.lower()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("fmt", "media_type", "marker"),
    [
        ("markdown", "text/markdown", b"# Transformers survey"),
        ("html", "text/html", b"<!DOCTYPE html>"),
        ("latex", "application/x-latex", b"\\documentclass"),
        ("docx", "wordprocessingml.document", b"PK"),
    ],
)
async def test_report_exports_in_each_available_format(
    client: AsyncClient, fmt: str, media_type: str, marker: bytes
) -> None:
    token = await _register_and_login(client, email="owner@example.com")
    project_id = await _create_project(client, token)
    report_id = await _create_report(client, token, project_id)

    response = await client.get(
        f"/api/v1/reports/{report_id}/export", params={"format": fmt}, headers=_auth(token)
    )

    assert response.status_code == 200
    assert media_type in response.headers["content-type"]
    assert response.headers["content-disposition"].startswith("attachment; filename=")
    assert marker in response.content


@pytest.mark.integration
async def test_docx_export_contains_the_report_title(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="owner@example.com")
    project_id = await _create_project(client, token)
    report_id = await _create_report(client, token, project_id, title="Graph networks")

    response = await client.get(
        f"/api/v1/reports/{report_id}/export", params={"format": "docx"}, headers=_auth(token)
    )

    paragraphs = [p.text for p in Document(io.BytesIO(response.content)).paragraphs]
    assert "Graph networks" in paragraphs


@pytest.mark.integration
async def test_export_with_a_non_ascii_title_does_not_break_the_response(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="owner@example.com")
    project_id = await _create_project(client, token)
    report_id = await _create_report(client, token, project_id, title="研究報告")

    response = await client.get(
        f"/api/v1/reports/{report_id}/export", params={"format": "markdown"}, headers=_auth(token)
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == "attachment; filename=report.md"


@pytest.mark.integration
async def test_unknown_export_format_is_rejected(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="owner@example.com")
    project_id = await _create_project(client, token)
    report_id = await _create_report(client, token, project_id)

    response = await client.get(
        f"/api/v1/reports/{report_id}/export", params={"format": "exe"}, headers=_auth(token)
    )

    assert response.status_code == 422


@pytest.mark.integration
async def test_another_users_report_is_not_found(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com")
    stranger = await _register_and_login(client, email="stranger@example.com")
    project_id = await _create_project(client, owner)
    report_id = await _create_report(client, owner, project_id)

    detail = await client.get(f"/api/v1/reports/{report_id}", headers=_auth(stranger))
    export = await client.get(
        f"/api/v1/reports/{report_id}/export", params={"format": "html"}, headers=_auth(stranger)
    )
    delete = await client.delete(f"/api/v1/reports/{report_id}", headers=_auth(stranger))
    listing = await client.get(f"/api/v1/projects/{project_id}/reports", headers=_auth(stranger))

    assert detail.status_code == 404
    assert export.status_code == 404
    assert delete.status_code == 404
    assert listing.status_code == 404


@pytest.mark.integration
async def test_unauthenticated_requests_are_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/reports/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 401


@pytest.mark.integration
async def test_deleted_report_is_gone(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="owner@example.com")
    project_id = await _create_project(client, token)
    report_id = await _create_report(client, token, project_id)

    delete = await client.delete(f"/api/v1/reports/{report_id}", headers=_auth(token))
    detail = await client.get(f"/api/v1/reports/{report_id}", headers=_auth(token))

    assert delete.status_code == 200
    assert detail.status_code == 404


@pytest.mark.integration
async def test_invalid_report_payload_is_rejected(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="owner@example.com")
    project_id = await _create_project(client, token)

    response = await client.post(
        f"/api/v1/projects/{project_id}/reports",
        json={"type": "not-a-type", "title": ""},
        headers=_auth(token),
    )

    assert response.status_code == 422
