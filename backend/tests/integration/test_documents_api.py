"""Integration tests for the documents API (design §6.5, FR-C).

Runs against a real database. Uploads exercise the synchronous half of
ingestion (validate → record → return ``pending``); the asynchronous pipeline
is verified separately in :mod:`tests.integration.test_ingestion_flow` so these
tests stay fast and do not depend on the embedding model.
"""

from __future__ import annotations

import io

import pytest
from docx import Document as DocxDocument
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


async def _create_project(client: AsyncClient, token: str) -> str:
    response = await client.post(
        "/api/v1/projects", json={"title": "Docs Project"}, headers=_auth_headers(token)
    )
    return str(response.json()["data"]["id"])


def _pdf_bytes(text: str = "Integration test PDF content.") -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    data = bytes(doc.tobytes())
    doc.close()
    return data


def _docx_bytes(text: str = "Integration test DOCX content.") -> bytes:
    document = DocxDocument()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.mark.integration
class TestUploadDocument:
    async def test_upload_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/documents",
            files={"file": ("paper.pdf", _pdf_bytes(), "application/pdf")},
        )
        assert response.status_code == 401

    async def test_upload_pdf_returns_pending_document(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="alice@example.com")
        project_id = await _create_project(client, token)

        response = await client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": ("paper.pdf", _pdf_bytes(), "application/pdf")},
            headers=_auth_headers(token),
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["filename"] == "paper.pdf"
        assert data["status"] == "pending"
        assert data["metadata"]["mime_type"] == "application/pdf"
        assert data["metadata"]["size_bytes"] > 0

    async def test_upload_docx_is_accepted(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="alice@example.com")
        project_id = await _create_project(client, token)

        response = await client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={
                "file": (
                    "paper.docx",
                    _docx_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            headers=_auth_headers(token),
        )

        assert response.status_code == 201
        assert response.json()["data"]["status"] == "pending"

    async def test_upload_rejects_unsupported_type(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="alice@example.com")
        project_id = await _create_project(client, token)

        response = await client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": ("notes.txt", b"plain text", "text/plain")},
            headers=_auth_headers(token),
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    async def test_upload_rejects_empty_file(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="alice@example.com")
        project_id = await _create_project(client, token)

        response = await client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": ("paper.pdf", b"", "application/pdf")},
            headers=_auth_headers(token),
        )

        assert response.status_code == 400

    async def test_upload_to_another_users_project_returns_404(self, client: AsyncClient) -> None:
        alice_token = await _register_and_login(client, email="alice@example.com")
        bob_token = await _register_and_login(client, email="bob@example.com")
        alice_project = await _create_project(client, alice_token)

        response = await client.post(
            f"/api/v1/projects/{alice_project}/documents",
            files={"file": ("paper.pdf", _pdf_bytes(), "application/pdf")},
            headers=_auth_headers(bob_token),
        )

        assert response.status_code == 404


@pytest.mark.integration
class TestListDocuments:
    async def test_lists_documents_in_a_project(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="alice@example.com")
        project_id = await _create_project(client, token)
        await client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": ("paper.pdf", _pdf_bytes(), "application/pdf")},
            headers=_auth_headers(token),
        )

        response = await client.get(
            f"/api/v1/projects/{project_id}/documents", headers=_auth_headers(token)
        )

        assert response.status_code == 200
        documents = response.json()["data"]
        assert len(documents) == 1
        assert documents[0]["filename"] == "paper.pdf"

    async def test_lists_only_the_projects_own_documents(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="alice@example.com")
        project_a = await _create_project(client, token)
        project_b = await _create_project(client, token)
        await client.post(
            f"/api/v1/projects/{project_a}/documents",
            files={"file": ("a.pdf", _pdf_bytes(), "application/pdf")},
            headers=_auth_headers(token),
        )

        response = await client.get(
            f"/api/v1/projects/{project_b}/documents", headers=_auth_headers(token)
        )

        assert response.json()["data"] == []

    async def test_listing_another_users_project_returns_404(self, client: AsyncClient) -> None:
        alice_token = await _register_and_login(client, email="alice@example.com")
        bob_token = await _register_and_login(client, email="bob@example.com")
        alice_project = await _create_project(client, alice_token)

        response = await client.get(
            f"/api/v1/projects/{alice_project}/documents", headers=_auth_headers(bob_token)
        )

        assert response.status_code == 404


@pytest.mark.integration
class TestGetDocument:
    async def test_returns_document_detail_and_status(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="alice@example.com")
        project_id = await _create_project(client, token)
        upload = await client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": ("paper.pdf", _pdf_bytes(), "application/pdf")},
            headers=_auth_headers(token),
        )
        document_id = upload.json()["data"]["id"]

        response = await client.get(
            f"/api/v1/documents/{document_id}", headers=_auth_headers(token)
        )

        assert response.status_code == 200
        assert response.json()["data"]["id"] == document_id
        assert response.json()["data"]["status"] in {"pending", "processing", "ready"}

    async def test_another_user_gets_404(self, client: AsyncClient) -> None:
        alice_token = await _register_and_login(client, email="alice@example.com")
        bob_token = await _register_and_login(client, email="bob@example.com")
        project_id = await _create_project(client, alice_token)
        upload = await client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": ("paper.pdf", _pdf_bytes(), "application/pdf")},
            headers=_auth_headers(alice_token),
        )
        document_id = upload.json()["data"]["id"]

        response = await client.get(
            f"/api/v1/documents/{document_id}", headers=_auth_headers(bob_token)
        )

        assert response.status_code == 404

    async def test_nonexistent_document_returns_404(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="alice@example.com")

        response = await client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000",
            headers=_auth_headers(token),
        )

        assert response.status_code == 404


@pytest.mark.integration
class TestDeleteDocument:
    async def test_deletes_a_document(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, email="alice@example.com")
        project_id = await _create_project(client, token)
        upload = await client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": ("paper.pdf", _pdf_bytes(), "application/pdf")},
            headers=_auth_headers(token),
        )
        document_id = upload.json()["data"]["id"]

        delete_response = await client.delete(
            f"/api/v1/documents/{document_id}", headers=_auth_headers(token)
        )
        get_response = await client.get(
            f"/api/v1/documents/{document_id}", headers=_auth_headers(token)
        )

        assert delete_response.status_code == 200
        assert get_response.status_code == 404

    async def test_another_user_cannot_delete(self, client: AsyncClient) -> None:
        alice_token = await _register_and_login(client, email="alice@example.com")
        bob_token = await _register_and_login(client, email="bob@example.com")
        project_id = await _create_project(client, alice_token)
        upload = await client.post(
            f"/api/v1/projects/{project_id}/documents",
            files={"file": ("paper.pdf", _pdf_bytes(), "application/pdf")},
            headers=_auth_headers(alice_token),
        )
        document_id = upload.json()["data"]["id"]

        delete_response = await client.delete(
            f"/api/v1/documents/{document_id}", headers=_auth_headers(bob_token)
        )
        get_response = await client.get(
            f"/api/v1/documents/{document_id}", headers=_auth_headers(alice_token)
        )

        assert delete_response.status_code == 404
        assert get_response.status_code == 200
