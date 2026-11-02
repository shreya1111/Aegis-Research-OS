"""Background-task entry points for analytics (design §6.7).

Both jobs run after the HTTP response is sent, so they open their own database
session rather than reusing the request-scoped one — the same contract the
ingestion and report runners follow.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.llm.registry import get_llm_provider
from app.core.logging import get_logger
from app.db.repositories.analytics_repository import AnalyticsRepository
from app.db.session import new_db_session
from app.services.analytics_service import AnalyticsService

logger = get_logger(__name__)


async def run_dataset_profiling(dataset_id: UUID, csv_content: bytes) -> None:
    """Profile an uploaded dataset and persist the result.

    Never raises: the job has no caller to surface an error to. Failures are
    recorded against the dataset row, and the ``except`` is *inside* the session
    context so that a failed mark is committed rather than rolled back with the
    exception.
    """
    settings = get_settings()
    try:
        async with new_db_session() as session:
            service = AnalyticsService(
                repository=AnalyticsRepository(session),
                llm_provider=get_llm_provider(settings),
            )
            try:
                await service.profile_dataset(dataset_id, csv_content)
            except Exception:
                logger.exception(
                    "analytics.profile_failed",
                    extra={
                        "event": "analytics.profile_failed",
                        "dataset_id": str(dataset_id),
                    },
                )
    except Exception:
        logger.exception(
            "analytics.profile_runner_failed",
            extra={
                "event": "analytics.profile_runner_failed",
                "dataset_id": str(dataset_id),
            },
        )


async def run_analysis(
    *,
    analysis_id: UUID,
    dataset_id: UUID,
    question: str,
    csv_content: bytes,
    profile_data: dict[str, Any],
) -> None:
    """Execute one AI-assisted analysis and persist its result."""
    settings = get_settings()
    try:
        async with new_db_session() as session:
            service = AnalyticsService(
                repository=AnalyticsRepository(session),
                llm_provider=get_llm_provider(settings),
            )
            try:
                await service.analyze_dataset(
                    analysis_id,
                    dataset_id,
                    question,
                    csv_content,
                    profile_data,
                )
            except Exception:
                logger.exception(
                    "analytics.analysis_failed",
                    extra={
                        "event": "analytics.analysis_failed",
                        "analysis_id": str(analysis_id),
                    },
                )
    except Exception:
        logger.exception(
            "analytics.analysis_runner_failed",
            extra={
                "event": "analytics.analysis_runner_failed",
                "analysis_id": str(analysis_id),
            },
        )
