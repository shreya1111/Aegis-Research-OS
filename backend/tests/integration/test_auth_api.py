"""Integration tests for the ``/auth`` router against a real database (FR-A)."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

REGISTER_PAYLOAD = {
    "email": "alice@example.com",
    "password": "correct-horse-battery",
    "name": "Alice",
}


async def _register(client: AsyncClient, **overrides: str) -> dict[str, Any]:
    payload = {**REGISTER_PAYLOAD, **overrides}
    response = await client.post("/api/v1/auth/register", json=payload)
    return dict(response.json())


async def _login(client: AsyncClient, *, email: str, password: str) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return dict(response.json())


@pytest.mark.integration
async def test_register_returns_the_created_profile_without_the_password(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "alice@example.com"
    assert body["data"]["name"] == "Alice"
    assert "password" not in body["data"]
    assert "hashed_password" not in body["data"]


@pytest.mark.integration
async def test_register_rejects_a_duplicate_email(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


@pytest.mark.integration
async def test_register_rejects_a_short_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "password": "short"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.integration
async def test_register_rejects_a_malformed_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "email": "not-an-email"},
    )

    assert response.status_code == 422


@pytest.mark.integration
async def test_login_returns_an_access_and_refresh_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.integration
async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.integration
async def test_login_with_unknown_email_matches_the_wrong_password_response(
    client: AsyncClient,
) -> None:
    """Login must not be a user-enumeration oracle (design §9.1)."""
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    unknown = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "irrelevant"},
    )
    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )

    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json()["error"] == wrong_password.json()["error"]


@pytest.mark.integration
async def test_me_returns_the_authenticated_profile(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login_body = await _login(
        client, email=REGISTER_PAYLOAD["email"], password=REGISTER_PAYLOAD["password"]
    )
    access_token = login_body["data"]["access_token"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["email"] == REGISTER_PAYLOAD["email"]


@pytest.mark.integration
async def test_me_without_a_token_is_unauthenticated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.integration
async def test_me_with_a_malformed_token_is_unauthenticated(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401


@pytest.mark.integration
async def test_refresh_issues_a_new_working_access_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login_body = await _login(
        client, email=REGISTER_PAYLOAD["email"], password=REGISTER_PAYLOAD["password"]
    )
    refresh_token = login_body["data"]["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    new_access_token = response.json()["data"]["access_token"]
    me_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert me_response.status_code == 200


@pytest.mark.integration
async def test_refresh_rejects_an_access_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login_body = await _login(
        client, email=REGISTER_PAYLOAD["email"], password=REGISTER_PAYLOAD["password"]
    )
    access_token = login_body["data"]["access_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401


@pytest.mark.integration
async def test_logout_revokes_the_access_token(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    login_body = await _login(
        client, email=REGISTER_PAYLOAD["email"], password=REGISTER_PAYLOAD["password"]
    )
    access_token = login_body["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    logout_response = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 200

    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 401


@pytest.mark.integration
async def test_every_response_carries_a_request_id(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.headers.get("X-Request-ID")
