"""The ingestion pipeline: extract → metadata → chunk → embed → persist
(design §6.4 "IngestionService", §8.1).

Owns the ``pending → processing → ready | failed`` lifecycle. Runs as a
background task dispatched by the API layer (design §6.7) so the upload
response never waits on processing.
"""

from __future__ import annotations

from uuid import UUID

from app.core.config import Settings
from app.core.logging import get_logger
from app.db.models.document import DocumentStatus
from app.db.repositories.document_chunk_repository import DocumentChunkRepository
from app.db.repositories.document_repository import DocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.ingestion.chunking import chunk_document
from app.services.ingestion.errors import ExtractionError
from app.services.ingestion.metadata import build_failure_metadata, build_metadata
from app.services.ingestion.parsers.docx import parse_docx
from app.services.ingestion.parsers.pdf import parse_pdf
from app.services.ingestion.types import ExtractedDocument

logger = get_logger(__name__)

#: MIME type → parser. Both parsers share the ExtractedDocument contract so
#: the rest of the pipeline is format-agnostic (design §8.2).
_PARSERS = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


class IngestionPipeline:
    """Runs one document through extraction, chunking, embedding, and
    persistence (design §6.4).

    Constructed with its collaborators rather than reaching for globals, so it
    is unit-testable with fakes (design: services are HTTP-free and DI-driven).
    """

    def __init__(
        self,
        *,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        embedding_service: EmbeddingService,
        settings: Settings,
    ) -> None:
        self._documents = document_repository
        self._chunks = chunk_repository
        self._embeddings = embedding_service
        self._settings = settings

    def _parse(self, *, mime_type: str, content: bytes) -> ExtractedDocument:
        parser_name = _PARSERS.get(mime_type)
        if parser_name == "pdf":
            return parse_pdf(
                content,
                ocr_enabled=self._settings.ocr_enabled,
                ocr_trigger_char_threshold=self._settings.ocr_trigger_char_threshold,
            )
        if parser_name == "docx":
            return parse_docx(content)
        # Unreachable in practice: validate_upload() already restricted the
        # MIME type before a document row was ever created.
        raise ExtractionError(f"No parser available for MIME type '{mime_type}'.")

    async def run(self, document_id: UUID, *, project_id: UUID, content: bytes) -> None:
        """Process one uploaded document end to end.

        Never raises: every failure is caught and recorded as
        ``documents.status = failed`` with a human-readable reason (design
        §6.10 principle 1 & 4, FR-C9 "No crash"). This method is the entry
        point a background task calls.
        """
        document = await self._documents.get_by_id_for_project(document_id, project_id=project_id)
        if document is None:
            # The document (or its project) was deleted before the background
            # task ran. Nothing to process, nothing to report — design §6.7
            # requires idempotent, safe-to-skip background work.
            logger.warning(
                "ingestion.document_missing",
                extra={"event": "ingestion.document_missing", "document_id": str(document_id)},
            )
            return

        mime_type = document.metadata_.get("mime_type", "")
        size_bytes = document.metadata_.get("size_bytes", len(content))

        await self._documents.update_status(document, status=DocumentStatus.PROCESSING)

        try:
            extracted = self._parse(mime_type=mime_type, content=content)

            if extracted.page_count > self._settings.max_upload_pages:
                raise ExtractionError(
                    f"This document has {extracted.page_count} pages, which exceeds the "
                    f"{self._settings.max_upload_pages}-page limit."
                )

            chunks = chunk_document(
                extracted,
                chunk_tokens=self._settings.chunk_tokens,
                chunk_overlap_tokens=self._settings.chunk_overlap_tokens,
            )

            # Re-running ingestion deletes and rebuilds rather than appending,
            # so a retry after a crash cannot produce duplicates (design §8.1).
            await self._chunks.delete_for_document(document_id)

            if chunks:
                embeddings = self._embeddings.embed_texts([chunk.content for chunk in chunks])
                await self._chunks.bulk_create(
                    document_id=document_id,
                    project_id=project_id,
                    chunks=chunks,
                    embeddings=embeddings,
                )

            metadata = build_metadata(
                extracted,
                mime_type=mime_type,
                size_bytes=size_bytes,
                ocr_confidence_threshold=self._settings.ocr_confidence_threshold,
            )
            await self._documents.update_status(
                document, status=DocumentStatus.READY, metadata=metadata
            )
            logger.info(
                "ingestion.completed",
                extra={
                    "event": "ingestion.completed",
                    "document_id": str(document_id),
                    "chunk_count": len(chunks),
                    "ocr_used": extracted.used_ocr,
                },
            )

        except ExtractionError as exc:
            await self._chunks.delete_for_document(document_id)
            metadata = build_failure_metadata(
                mime_type=mime_type, size_bytes=size_bytes, failure_reason=str(exc)
            )
            await self._documents.update_status(
                document, status=DocumentStatus.FAILED, metadata=metadata
            )
            logger.warning(
                "ingestion.failed",
                extra={
                    "event": "ingestion.failed",
                    "document_id": str(document_id),
                    "reason": str(exc),
                },
            )
        except Exception:
            # Any unexpected failure is still isolated to this one document
            # (design §8.1 "Isolate": "A failure affects exactly one
            # document") rather than propagating out of the background task.
            await self._chunks.delete_for_document(document_id)
            metadata = build_failure_metadata(
                mime_type=mime_type,
                size_bytes=size_bytes,
                failure_reason="An unexpected error occurred while processing this document.",
            )
            await self._documents.update_status(
                document, status=DocumentStatus.FAILED, metadata=metadata
            )
            logger.exception(
                "ingestion.unexpected_error",
                extra={"event": "ingestion.unexpected_error", "document_id": str(document_id)},
            )
