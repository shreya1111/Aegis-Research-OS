"""Background-task entry point for report generation (Phase 6 + Phase 10).

Opens its own database session, exactly as the ingestion runner does (design
§6.7), because this runs after the HTTP response has been sent. On completion it
records the action in the project's audit log and notifies the user who asked
for the artifact — the Phase 10 requirement that a long-running generation
reports back without the user watching the page.
"""

from __future__ import annotations

from uuid import UUID

from app.core.logging import get_logger
from app.db.models.activity import ActivityAction
from app.db.repositories.activity_repository import ActivityRepository
from app.db.repositories.notification_repository import NotificationRepository
from app.db.repositories.report_repository import ReportRepository
from app.db.session import new_db_session
from app.services.activity_service import ActivityService
from app.services.agent_service_mock import MockAgentService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService

logger = get_logger(__name__)


async def run_report_generation(
    *,
    report_id: UUID,
    project_id: UUID,
    user_id: UUID,
    report_title: str,
) -> None:
    """Generate one artifact, then log it and notify the requester.

    Never raises: a background task's exception has nowhere to surface, so both
    failure paths are recorded against the report row / audit log instead.
    """
    try:
        async with new_db_session() as session:
            report_repository = ReportRepository(session)
            report = await report_repository.get_by_id_for_project(report_id, project_id)
            if report is None:
                logger.warning(
                    "report.runner.missing",
                    extra={"event": "report.runner.missing", "report_id": str(report_id)},
                )
                return

            service = ReportService(
                report_repository=report_repository,
                agent_service=MockAgentService(),
            )

            succeeded = True
            try:
                await service.generate_report(report)
            except Exception:
                succeeded = False
                logger.exception(
                    "report.runner.failed",
                    extra={"event": "report.runner.failed", "report_id": str(report_id)},
                )

            activity = ActivityService(activity_repository=ActivityRepository(session))
            await activity.record(
                project_id=project_id,
                user_id=user_id,
                action=(
                    ActivityAction.REPORT_GENERATED
                    if succeeded
                    else ActivityAction.REPORT_FAILED
                ),
                entity_type="report",
                entity_id=report_id,
                context={"title": report_title},
            )

            notifications = NotificationService(
                notification_repository=NotificationRepository(session)
            )
            await notifications.notify_report_completed(
                user_id=user_id,
                project_id=project_id,
                report_title=report_title,
                succeeded=succeeded,
            )
    except Exception:
        logger.exception(
            "report.runner.session_failed",
            extra={"event": "report.runner.session_failed", "report_id": str(report_id)},
        )
