"""``GET /projects/{id}/traces/{run_id}`` — agent reasoning trace (design §6.5, §4.6)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import AgentTraceRepositoryDep
from app.api.v1.deps import ProjectInScopeDep
from app.core.envelope import ok
from app.core.errors import NotFoundError
from app.schemas.common import ApiResponse
from app.schemas.trace import TraceRunRead, TraceStepRead

router = APIRouter(tags=["traces"])


@router.get(
    "/projects/{project_id}/traces/{run_id}",
    response_model=ApiResponse[TraceRunRead],
    summary="Get the ordered agent reasoning trace for one run",
)
async def get_trace(
    project: ProjectInScopeDep,
    run_id: UUID,
    trace_repository: AgentTraceRepositoryDep,
) -> ApiResponse[TraceRunRead]:
    traces = await trace_repository.list_for_run(run_id, project_id=project.id)
    if not traces:
        raise NotFoundError("Trace run not found.")
    return ok(
        TraceRunRead(run_id=run_id, steps=[TraceStepRead.from_model(trace) for trace in traces])
    )
