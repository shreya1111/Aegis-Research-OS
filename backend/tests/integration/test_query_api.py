"""Integration tests for ``POST /projects/{id}/query`` (design §6.5, FR-D, FR-E).

Runs against a real database with the LLM provider dependency overridden by a
deterministic fake — retrieval, citation validation, persistence, and the
Phase 4 / Phase 5 routing heuristic are all exercised for real; only the
network call to an actual model provider is stubbed.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.deps import get_llm_provider_dep
from app.core.llm.provider import LLMResponse, Message, ModelTier


class _FakeLLMProvider:
    """Deterministic stand-in for a real LLM provider.

    Recognises the system prompts used by :class:`RagService` and the Phase 5
    agent nodes (design §4.6 roster) so both pipelines produce a valid,
    citeable answer without any network call.
    """

    async def complete(
        self,
        messages: list[Message],
        model_tier: ModelTier,
        max_tokens: int,
        tools: list[dict[str, object]] | None = None,
    ) -> LLMResponse:
        system_prompt = messages[0].content if messages else ""
        if "research supervisor" in system_prompt:
            text = "1. Answer the question\nEXTERNAL: no"
        elif "Summarise" in system_prompt:
            text = "A summary of the retrieved material."
        elif "fact-checking" in system_prompt:
            text = "ALL SUPPORTED"
        elif "composing the final" in system_prompt or "research assistant" in system_prompt:
            text = "This is the answer, with no sources available to cite."
        elif "reviewing a synthesised" in system_prompt:
            text = "APPROVED"
        else:
            text = "This is the answer, with no sources available to cite."
        return LLMResponse(
            text=text,
            tokens_in=10,
            tokens_out=10,
            model_used="fake-model",
            estimated_cost_usd=0.0,
        )


@pytest.fixture(autouse=True)
def _override_llm_provider(app: FastAPI) -> None:
    app.dependency_overrides[get_llm_provider_dep] = lambda: _FakeLLMProvider()


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
        "/api/v1/projects", json={"title": "Query Project"}, headers=_auth_headers(token)
    )
    return str(response.json()["data"]["id"])


@pytest.mark.integration
async def test_query_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/query",
        json={"question": "What is the main finding?"},
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_a_simple_question_is_answered_via_the_rag_pipeline(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="alice@example.com")
    project_id = await _create_project(client, token)

    response = await client.post(
        f"/api/v1/projects/{project_id}/query",
        json={"question": "What is the main finding?"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pipeline"] == "rag"
    assert data["answer"]
    assert data["run_id"]
    assert data["message_id"]


@pytest.mark.integration
async def test_a_multi_part_research_question_is_routed_to_the_agent_graph(
    client: AsyncClient,
) -> None:
    """Phase 5 acceptance criteria: a multi-part research question routes
    through the agent graph rather than the Phase 4 fast path."""
    token = await _register_and_login(client, email="alice@example.com")
    project_id = await _create_project(client, token)

    response = await client.post(
        f"/api/v1/projects/{project_id}/query",
        json={"question": "Compare approach A and B and identify open gaps."},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pipeline"] == "agent"
    assert data["answer"]


@pytest.mark.integration
async def test_agent_run_trace_is_retrievable_after_the_query_completes(
    client: AsyncClient,
) -> None:
    """FR-E7: ``GET /projects/{id}/traces/{run_id}`` returns the ordered
    trace for a completed agent run."""
    token = await _register_and_login(client, email="alice@example.com")
    project_id = await _create_project(client, token)

    query_response = await client.post(
        f"/api/v1/projects/{project_id}/query",
        json={"question": "Compare approach A and B and identify open gaps."},
        headers=_auth_headers(token),
    )
    run_id = query_response.json()["data"]["run_id"]

    trace_response = await client.get(
        f"/api/v1/projects/{project_id}/traces/{run_id}", headers=_auth_headers(token)
    )

    assert trace_response.status_code == 200
    steps = trace_response.json()["data"]["steps"]
    assert len(steps) > 0
    agent_names = {step["agent_name"] for step in steps}
    # Design §4.6 roster: at minimum, a multi-part request should visibly
    # trigger the Supervisor and the Synthesis/Report-Writer agent.
    assert "Supervisor/Planner" in agent_names
    assert "Synthesis/Report-Writer" in agent_names


@pytest.mark.integration
async def test_query_for_another_users_project_returns_404(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, email="alice@example.com")
    bob_token = await _register_and_login(client, email="bob@example.com")
    alice_project = await _create_project(client, alice_token)

    response = await client.post(
        f"/api/v1/projects/{alice_project}/query",
        json={"question": "What is the main finding?"},
        headers=_auth_headers(bob_token),
    )

    assert response.status_code == 404


@pytest.mark.integration
async def test_query_rejects_an_empty_question(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="alice@example.com")
    project_id = await _create_project(client, token)

    response = await client.post(
        f"/api/v1/projects/{project_id}/query",
        json={"question": ""},
        headers=_auth_headers(token),
    )

    assert response.status_code == 422
