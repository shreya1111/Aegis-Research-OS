"""Integration tests for the wired application: health, envelope, headers, errors."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.middleware import REQUEST_ID_HEADER
from app.main import create_app


@pytest.mark.integration
async def test_health_returns_success_envelope(client: AsyncClient, settings: Settings) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"] == {
        "status": "ok",
        "service": settings.project_name,
        "version": settings.version,
        "environment": "development",
    }


@pytest.mark.integration
async def test_response_carries_request_id_header(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.headers[REQUEST_ID_HEADER]


@pytest.mark.integration
async def test_inbound_request_id_is_preserved(client: AsyncClient) -> None:
    response = await client.get("/health", headers={REQUEST_ID_HEADER: "trace-me"})
    assert response.headers[REQUEST_ID_HEADER] == "trace-me"


@pytest.mark.integration
async def test_security_headers_are_applied(client: AsyncClient) -> None:
    headers = (await client.get("/health")).headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    # HSTS is meaningless without TLS, so development must not advertise it.
    assert "Strict-Transport-Security" not in headers


@pytest.mark.integration
async def test_unknown_route_returns_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.integration
async def test_docs_are_served_outside_production(client: AsyncClient) -> None:
    assert (await client.get("/openapi.json")).status_code == 200


@pytest.mark.integration
async def test_docs_are_disabled_in_production() -> None:
    app: FastAPI = create_app(
        Settings(
            environment="production",
            log_level="WARNING",
            jwt_secret="a-real-production-secret-value",
        )
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as production_client:
        assert (await production_client.get("/openapi.json")).status_code == 404
        assert (await production_client.get("/docs")).status_code == 404
        response = await production_client.get("/health")

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
