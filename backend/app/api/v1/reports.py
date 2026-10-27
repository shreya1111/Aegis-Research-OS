"""``/projects/{id}/reports`` and ``/reports/{id}`` routers (Phase 6 research artifacts)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status
from fastapi.responses import Response

from app.api.deps import CurrentUserDep, DbSessionDep, SettingsDep
from app.api.v1.deps import ProjectInScopeDep
from app.core.envelope import ok
from app.core.errors import NotFoundError
from app.db.repositories.report_repository import ReportRepository
from app.schemas.common import ApiResponse
from app.schemas.report import ReportCreate, ReportRead
from app.services.export_service import ExportFormat, ExportService
from app.services.report_service import ReportService

router = APIRouter(tags=["reports"])


def _get_report_service(session: DbSessionDep, settings: SettingsDep) -> ReportService:
    """Build a ReportService with its dependencies."""
    # For Phase 6 MVP, use simplified report generation without full agent orchestration
    # This can be enhanced later when the agent system is fully integrated
    report_repository = ReportRepository(session)

    # Create a simple mock agent service for now that generates basic content
    from app.services.agent_service_mock import MockAgentService

    mock_agent_service = MockAgentService()

    return ReportService(
        report_repository=report_repository,
        agent_service=mock_agent_service,
    )


@router.post(
    "/projects/{project_id}/reports",
    response_model=ApiResponse[ReportRead],
    status_code=status.HTTP_201_CREATED,
    summary="Generate a research artifact",
)
async def create_report(
    project: ProjectInScopeDep,
    payload: ReportCreate,
    background_tasks: BackgroundTasks,
    session: DbSessionDep,
    settings: SettingsDep,
) -> ApiResponse[ReportRead]:
    """Create and generate a research artifact (literature review, survey, etc.)."""
    report_service = _get_report_service(session, settings)

    # Create the report record
    report = await report_service.create_report(
        project_id=project.id,
        type=payload.type,
        title=payload.title,
    )

    # Commit the pending report before scheduling background generation
    await session.commit()

    # Schedule background generation
    background_tasks.add_task(report_service.generate_report, report)

    return ok(ReportRead.from_model(report))


@router.get(
    "/projects/{project_id}/reports",
    response_model=ApiResponse[list[ReportRead]],
    summary="List reports for a project",
)
async def list_reports(
    project: ProjectInScopeDep,
    session: DbSessionDep,
    settings: SettingsDep,
) -> ApiResponse[list[ReportRead]]:
    """List all generated reports for a project."""
    report_service = _get_report_service(session, settings)
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
    settings: SettingsDep,
) -> ApiResponse[ReportRead]:
    """Get a specific report by ID."""
    # Note: This is a simplified version. A proper implementation would
    # need to check project ownership through the user's projects
    # For now, we'll need to get the project_id from the report and validate access

    # This is a temporary solution - should be improved with proper access control
    from sqlalchemy import select

    from app.db.models.project import Project
    from app.db.models.report import Report

    stmt = (
        select(Report, Project)
        .join(Project, Report.project_id == Project.id)
        .where(Report.id == report_id, Project.owner_id == current_user.id)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        raise NotFoundError("Report not found")

    report = row[0]
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
    settings: SettingsDep,
) -> ApiResponse[None]:
    """Delete a report."""
    # Similar access control logic as get_report
    from sqlalchemy import select

    from app.db.models.project import Project
    from app.db.models.report import Report

    stmt = (
        select(Report, Project)
        .join(Project, Report.project_id == Project.id)
        .where(Report.id == report_id, Project.owner_id == current_user.id)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        raise NotFoundError("Report not found")

    report = row[0]
    report_service = _get_report_service(session, settings)
    await report_service.delete_report(report)

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
) -> Response:
    """Export a report in the specified format (PDF, DOCX, LaTeX, HTML)."""
    # Get the report with access control
    from sqlalchemy import select

    from app.db.models.project import Project
    from app.db.models.report import Report

    stmt = (
        select(Report, Project)
        .join(Project, Report.project_id == Project.id)
        .where(Report.id == report_id, Project.owner_id == current_user.id)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        raise NotFoundError("Report not found")

    report = row[0]

    # Export the report
    export_service = ExportService()
    content, filename, content_type = await export_service.export_report(report, format)

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
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
    settings: SettingsDep,
) -> ApiResponse[str]:
    """Generate a 1-page executive summary of the report using AI."""
    # Get the report with access control
    from sqlalchemy import select

    from app.db.models.project import Project
    from app.db.models.report import Report

    stmt = (
        select(Report, Project)
        .join(Project, Report.project_id == Project.id)
        .where(Report.id == report_id, Project.owner_id == current_user.id)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is None:
        raise NotFoundError("Report not found")

    report = row[0]
    
    if report.status != "completed" or not report.content_markdown:
        raise ValueError("Report must be completed before generating summary")

    # Generate executive summary
    report_service = _get_report_service(session, settings)
    summary = await report_service.generate_executive_summary(report)

    return ok(summary)
