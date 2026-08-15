"""Background-task entry point for the ingestion pipeline (design §6.7).

Opens its own database session rather than reusing a request-scoped one, since
this runs after the HTTP response has already been sent.
"""

from __future__ import annotations

from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories.document_chunk_repository import DocumentChunkRepository
from app.db.repositories.document_repository import DocumentRepository
from app.db.session import new_db_session
from app.services.embedding_service import get_embedding_service
from app.services.ingestion.pipeline import IngestionPipeline

logger = get_logger(__name__)


async def run_ingestion(document_id: UUID, project_id: UUID, content: bytes) -> None:
    """Process one document in a fresh session (design §6.7 background job
    contract: idempotent, isolated per document).

    Never raises: :meth:`IngestionPipeline.run` already catches and records
    every failure against the document itself. A failure to even open a
    session is logged so it is not silently lost.
    """
    settings = get_settings()
    try:
        async with new_db_session() as session:
            pipeline = IngestionPipeline(
                document_repository=DocumentRepository(session),
                chunk_repository=DocumentChunkRepository(session),
                embedding_service=get_embedding_service(settings),
                settings=settings,
            )
            await pipeline.run(document_id, project_id=project_id, content=content)
    except Exception:
        logger.exception(
            "ingestion.runner_failed",
            extra={"event": "ingestion.runner_failed", "document_id": str(document_id)},
        )
