"""Integration tests for Phase 10 collaboration: roles, audit log, notifications.

Every case drives the public API rather than the services directly, so the tests
cover the wiring (dependencies, envelope, status codes) that the feature actually
ships. Roles are asserted at the HTTP boundary because that is where the security
boundary lives (design §2.2).
"""

from __future__ import annotations

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


async def _create_project(client: AsyncClient, token: str, title: str = "Shared project") -> str:
    response = await client.post("/api/v1/projects", json={"title": title}, headers=_auth(token))
    assert response.status_code == 201
    return str(response.json()["data"]["id"])


async def _invite(
    client: AsyncClient, token: str, project_id: str, email: str, role: str
) -> object:
    return await client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"email": email, "role": role},
        headers=_auth(token),
    )


@pytest.mark.integration
async def test_owner_can_invite_a_viewer_and_the_roster_lists_both(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    await _register_and_login(client, email="viewer@example.com", name="Viewer")
    project_id = await _create_project(client, owner)

    response = await _invite(client, owner, project_id, "viewer@example.com", "viewer")

    assert response.status_code == 201
    roster = response.json()["data"]
    assert [member["role"] for member in roster] == ["owner", "viewer"]
    assert roster[0]["id"] is None, "the owner has no membership row"
    assert roster[1]["email"] == "viewer@example.com"
    assert roster[1]["id"] is not None


@pytest.mark.integration
async def test_invited_project_appears_in_the_members_dashboard(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    viewer = await _register_and_login(client, email="viewer@example.com", name="Viewer")
    project_id = await _create_project(client, owner)
    await _invite(client, owner, project_id, "viewer@example.com", "editor")

    response = await client.get("/api/v1/projects", headers=_auth(viewer))

    body = response.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["id"] == project_id
    assert body["items"][0]["role"] == "editor", "the dashboard needs the caller's role"


@pytest.mark.integration
async def test_viewer_can_read_but_not_write(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    viewer = await _register_and_login(client, email="viewer@example.com", name="Viewer")
    project_id = await _create_project(client, owner)
    await _invite(client, owner, project_id, "viewer@example.com", "viewer")

    read = await client.get(f"/api/v1/projects/{project_id}", headers=_auth(viewer))
    roster = await client.get(f"/api/v1/projects/{project_id}/members", headers=_auth(viewer))
    upload = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("notes.pdf", b"hello", "application/pdf")},
        headers=_auth(viewer),
    )
    report = await client.post(
        f"/api/v1/projects/{project_id}/reports",
        json={"type": "literature_review", "title": "Viewer report"},
        headers=_auth(viewer),
    )

    assert read.status_code == 200
    assert roster.status_code == 200
    assert upload.status_code == 403
    assert upload.json()["error"]["code"] == "FORBIDDEN"
    assert report.status_code == 403


@pytest.mark.integration
async def test_editor_can_upload_but_not_manage_members_or_delete(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    editor = await _register_and_login(client, email="editor@example.com", name="Editor")
    project_id = await _create_project(client, owner)
    await _invite(client, owner, project_id, "editor@example.com", "editor")

    upload = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("notes.pdf", b"hello world", "application/pdf")},
        headers=_auth(editor),
    )
    invite = await _invite(client, editor, project_id, "someone@example.com", "viewer")
    delete = await client.delete(f"/api/v1/projects/{project_id}", headers=_auth(editor))

    assert upload.status_code == 201
    assert invite.status_code == 403, "membership management is owner-only"
    assert delete.status_code == 403


@pytest.mark.integration
async def test_role_change_and_removal_take_effect_immediately(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    member = await _register_and_login(client, email="member@example.com", name="Member")
    project_id = await _create_project(client, owner)
    invited = await _invite(client, owner, project_id, "member@example.com", "viewer")
    member_id = invited.json()["data"][1]["id"]

    promoted = await client.patch(
        f"/api/v1/projects/{project_id}/members/{member_id}",
        json={"role": "editor"},
        headers=_auth(owner),
    )
    upload_after_promotion = await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("notes.pdf", b"hello", "application/pdf")},
        headers=_auth(member),
    )

    removed = await client.delete(
        f"/api/v1/projects/{project_id}/members/{member_id}", headers=_auth(owner)
    )
    access_after_removal = await client.get(f"/api/v1/projects/{project_id}", headers=_auth(member))

    assert promoted.status_code == 200
    assert [row["role"] for row in promoted.json()["data"]] == ["owner", "editor"]
    assert upload_after_promotion.status_code == 201
    assert removed.status_code == 200
    assert [row["role"] for row in removed.json()["data"]] == ["owner"]
    assert access_after_removal.status_code == 404, "removal reverts to indistinguishable 404"


@pytest.mark.integration
async def test_inviting_a_stranger_or_an_existing_member_is_rejected(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    await _register_and_login(client, email="other@example.com", name="Other")
    project_id = await _create_project(client, owner)

    unknown = await _invite(client, owner, project_id, "nobody@example.com", "viewer")
    first = await _invite(client, owner, project_id, "other@example.com", "viewer")
    duplicate = await _invite(client, owner, project_id, "other@example.com", "editor")
    owner_invite = await _invite(client, owner, project_id, "owner@example.com", "editor")

    assert unknown.status_code == 404
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert owner_invite.status_code == 409, "an existing owner is not invited again"


@pytest.mark.integration
async def test_ownership_cannot_be_granted_by_invitation(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    await _register_and_login(client, email="other@example.com", name="Other")
    project_id = await _create_project(client, owner)

    response = await _invite(client, owner, project_id, "other@example.com", "owner")

    assert response.status_code == 409


@pytest.mark.integration
async def test_non_member_sees_404_on_collaboration_endpoints(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    stranger = await _register_and_login(client, email="stranger@example.com", name="Stranger")
    project_id = await _create_project(client, owner)

    members = await client.get(f"/api/v1/projects/{project_id}/members", headers=_auth(stranger))
    activity = await client.get(f"/api/v1/projects/{project_id}/activity", headers=_auth(stranger))
    usage = await client.get(f"/api/v1/projects/{project_id}/usage", headers=_auth(stranger))
    invite = await _invite(client, stranger, project_id, "owner@example.com", "viewer")

    assert members.status_code == 404
    assert activity.status_code == 404
    assert usage.status_code == 404
    assert invite.status_code == 404


@pytest.mark.integration
async def test_upload_and_query_actions_reach_the_audit_log(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    project_id = await _create_project(client, owner)

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": ("paper.pdf", b"the quick brown fox", "application/pdf")},
        headers=_auth(owner),
    )

    response = await client.get(f"/api/v1/projects/{project_id}/activity", headers=_auth(owner))

    assert response.status_code == 200
    entries = response.json()["data"]["items"]
    actions = {entry["action"] for entry in entries}
    assert "document.uploaded" in actions
    uploaded = next(entry for entry in entries if entry["action"] == "document.uploaded")
    assert uploaded["context"] == {"filename": "paper.pdf"}
    assert uploaded["actor_name"] == "Owner"
    assert uploaded["entity_type"] == "document"


@pytest.mark.integration
async def test_usage_reports_zero_for_a_project_with_no_agent_runs(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    project_id = await _create_project(client, owner)

    response = await client.get(f"/api/v1/projects/{project_id}/usage", headers=_auth(owner))

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["run_count"] == 0
    assert body["trace_count"] == 0
    assert body["tokens_used"] == 0
    assert body["by_agent"] == []


@pytest.mark.integration
async def test_invitations_and_activity_are_notifications_for_the_invitee(
    client: AsyncClient,
) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    invitee = await _register_and_login(client, email="invitee@example.com", name="Invitee")
    project_id = await _create_project(client, owner, title="Shared workspace")
    await _invite(client, owner, project_id, "invitee@example.com", "viewer")

    inbox = await client.get("/api/v1/notifications", headers=_auth(invitee))
    owners_inbox = await client.get("/api/v1/notifications", headers=_auth(owner))

    assert inbox.status_code == 200
    body = inbox.json()["data"]
    assert body["unread"] == 1
    assert body["items"][0]["type"] == "member.added"
    assert body["items"][0]["link"] == f"/projects/{project_id}"
    assert owners_inbox.json()["data"]["items"] == [], "the actor is not notified"


@pytest.mark.integration
async def test_marking_a_notification_read_is_scoped_to_its_owner(client: AsyncClient) -> None:
    owner = await _register_and_login(client, email="owner@example.com", name="Owner")
    invitee = await _register_and_login(client, email="invitee@example.com", name="Invitee")
    intruder = await _register_and_login(client, email="intruder@example.com", name="Intruder")
    project_id = await _create_project(client, owner)
    await _invite(client, owner, project_id, "invitee@example.com", "viewer")
    notification_id = (await client.get("/api/v1/notifications", headers=_auth(invitee))).json()[
        "data"
    ]["items"][0]["id"]

    foreign = await client.post(
        f"/api/v1/notifications/{notification_id}/read", headers=_auth(intruder)
    )
    own = await client.post(f"/api/v1/notifications/{notification_id}/read", headers=_auth(invitee))
    after = await client.get("/api/v1/notifications", headers=_auth(invitee))

    assert foreign.status_code == 404
    assert own.status_code == 200
    assert after.json()["data"]["unread"] == 0
