"""``POST /projects/{id}/query`` — hybrid RAG or the agent graph (design
§6.5: "Runs RAG (Phase 4) or the agent graph (Phase 5+)")."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import AgentServiceDep, CurrentUserDep, RagServiceDep, RateLimiterDep, SettingsDep
from app.api.v1.deps import ProjectInScopeDep
from app.core.envelope import ok
from app.core.errors import RateLimitError
from app.schemas.common import ApiResponse
from app.schemas.query import QueryRequest, QueryResponse
from app.services.query_routing import requires_agent_pipeline
from app.services.retrieval.types import RetrievalFilters

router = APIRouter(tags=["query"])


@router.post(
    "/projects/{project_id}/query",
    response_model=ApiResponse[QueryResponse],
    status_code=status.HTTP_200_OK,
    summary="Answer a research question, routing to the agent graph for multi-part requests",
)
async def run_query(
    project: ProjectInScopeDep,
    body: QueryRequest,
    rag_service: RagServiceDep,
    agent_service: AgentServiceDep,
    current_user: CurrentUserDep,
    rate_limiter: RateLimiterDep,
    settings: SettingsDep,
) -> ApiResponse[QueryResponse]:
    # Highest-value rate limit in the system (design §9.6): bounds LLM cost
    # exhaustion, keyed per user rather than per IP since cost is incurred
    # per account.
    allowed = await rate_limiter.check(
        "query:user",
        str(current_user.id),
        limit=settings.rate_limit_query_per_minute,
        window_seconds=60,
    )
    if not allowed:
        raise RateLimitError("Too many questions. Please wait a moment and try again.")

    # A multi-part research request needs the Supervisor to decompose it
    # into subtasks; a single factual lookup stays on the Phase 4 fast path
    # rather than paying for a full agent graph (design §4.2).
    if requires_agent_pipeline(body.question):
        result = await agent_service.run(
            project_id=project.id,
            request=body.question,
            conversation_id=body.conversation_id,
        )
        return ok(QueryResponse.from_agent_result(result))

    filters = None
    if body.filters is not None:
        filters = RetrievalFilters(
            document_ids=body.filters.document_ids,
            uploaded_after=body.filters.uploaded_after,
            uploaded_before=body.filters.uploaded_before,
        )

    answer = await rag_service.answer_question(
        project_id=project.id,
        question=body.question,
        filters=filters,
        conversation_id=body.conversation_id,
    )
    return ok(QueryResponse.from_answer(answer))
