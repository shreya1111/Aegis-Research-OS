"""``/projects/{id}/reports`` and ``/reports/{id}`` routers (Phase 6 + Phase 10)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status
from fastapi.responses import Response

from app.api.deps import (
    CurrentUserDep,
    DbSessionDep,
    MembershipServiceDep,
    ProjectServiceDep,
)
from app.api.v1.deps import ProjectEditorDep, ProjectInScopeDep, resolve_project_access
from app.core.envelope import ok
from app.core.errors import NotFoundError, ValidationError
from app.db.models.report import Report
from app.db.repositories.report_repository import ReportRepository
from app.schemas.common import ApiResponse
from app.schemas.report import ReportCreate, ReportRead
from app.services.agent_service_mock import MockAgentService
from app.services.export_service import ExportFormat, ExportService
from app.services.report_runner import run_report_generation
from app.services.report_service import ReportService

router = APIRouter(tags=["reports"])


def _get_report_service(session: DbSessionDep) -> ReportService:
    """Build a ReportService with its dependencies.

    Generation still runs on the Phase 6 mock (see ``agent_service_mock``), so an
    artifact is templated rather than retrieved from the project corpus. Swapping
    in the real ``AgentService`` is a one-line change in the runner once the
    artifact path is wired to the agent graph.
    """
    return ReportService(
        report_repository=ReportRepository(session),
        agent_service=MockAgentService(),
    )


async def _report_for_caller(
    report_id: UUID,
    *,
    current_user: CurrentUserDep,
    session: DbSessionDep,
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> Report:
    """Load a report and authorise the caller against its project.

    ``/reports/{id}`` carries no project id, so the tenancy check happens on the
    loaded row's ``project_id``. A report outside the caller's access raises 404
    through the shared project-scope helper, exactly like a project-scoped route.
    """
    report = await ReportRepository(session).get_by_id(report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    await resolve_project_access(
        report.project_id,
        user_id=current_user.id,
        project_service=project_service,
        membership_service=membership_service,
    )
    return report


@router.post(
    "/projects/{project_id}/reports",
    response_model=ApiResponse[ReportRead],
    status_code=status.HTTP_201_CREATED,
    summary="Generate a research artifact",
)
async def create_report(
    project: ProjectEditorDep,
    payload: ReportCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
    session: DbSessionDep,
) -> ApiResponse[ReportRead]:
    """Create a research artifact and generate it in the background.

    The audit entry and the completion notification are written by the runner, so
    they describe what actually happened (FR-H7) rather than what was requested.
    """
    report_service = _get_report_service(session)
    report = await report_service.create_report(
        project_id=project.id,
        type=payload.type,
        title=payload.title,
    )

    # Durable before dispatch, for the same reason uploads commit first: the
    # background task opens its own session and must be able to see the row.
    await session.commit()

    background_tasks.add_task(
        run_report_generation,
        report_id=report.id,
        project_id=project.id,
        user_id=current_user.id,
        report_title=report.title,
    )

    return ok(ReportRead.from_model(report))


@router.get(
    "/projects/{project_id}/reports",
    response_model=ApiResponse[list[ReportRead]],
    summary="List reports for a project",
)
async def list_reports(
    project: ProjectInScopeDep,
    session: DbSessionDep,
) -> ApiResponse[list[ReportRead]]:
    report_service = _get_report_service(session)
    reports = await report_service.list_reports(project.id)
    return ok([ReportRead.from_model(report) for report in reports])


@router.get(
    "/reports/{report_id}",
    response_model=ApiResponse[ReportRead],
    summary="Get report details",
)
async def get_report(
    report_id: UUID,
    current_user: CurrentUserDep,
    session: DbSessionDep,
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[ReportRead]:
    report = await _report_for_caller(
        report_id,
        current_user=current_user,
        session=session,
        project_service=project_service,
        membership_service=membership_service,
    )
    return ok(ReportRead.from_model(report))


@router.delete(
    "/reports/{report_id}",
    response_model=ApiResponse[None],
    summary="Delete a report",
)
async def delete_report(
    report_id: UUID,
    current_user: CurrentUserDep,
    session: DbSessionDep,
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[None]:
    report = await _report_for_caller(
        report_id,
        current_user=current_user,
        session=session,
        project_service=project_service,
        membership_service=membership_service,
    )
    await _get_report_service(session).delete_report(report)
    return ok(None)


@router.get(
    "/reports/{report_id}/export",
    summary="Export a report in the specified format",
)
async def export_report(
    report_id: UUID,
    format: ExportFormat,
    current_user: CurrentUserDep,
    session: DbSessionDep,
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> Response:
    """Export a report in the specified format (PDF, DOCX, LaTeX, HTML)."""
    report = await _report_for_caller(
        report_id,
        current_user=current_user,
        session=session,
        project_service=project_service,
        membership_service=membership_service,
    )

    content, filename, content_type = await ExportService().export_report(report, format)

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post(
    "/reports/{report_id}/summary",
    response_model=ApiResponse[str],
    summary="Generate executive summary",
)
async def generate_summary(
    report_id: UUID,
    current_user: CurrentUserDep,
    session: DbSessionDep,
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[str]:
    """Generate a 1-page executive summary of the report using AI."""
    report = await _report_for_caller(
        report_id,
        current_user=current_user,
        session=session,
        project_service=project_service,
        membership_service=membership_service,
    )

    if report.status != "completed" or not report.content_markdown:
        raise ValidationError("Report must be completed before generating a summary.")

    summary = await _get_report_service(session).generate_executive_summary(report)
    return ok(summary)
