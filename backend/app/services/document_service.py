"""Document upload, listing, and deletion (design §6.4 "IngestionService" entry
points, FR-C).

Owns the synchronous half of ingestion (validate, record, dispatch); the
asynchronous half is :class:`app.services.ingestion.pipeline.IngestionPipeline`,
run by a background task this service schedules.
"""

from __future__ import annotations

from uuid import UUID

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.db.models.document import Document
from app.db.repositories.document_repository import DocumentRepository
from app.services.ingestion.validation import sanitise_filename, validate_upload


class DocumentService:
    """Business logic for the Documents tab (design FR-C)."""

    def __init__(
        self,
        *,
        document_repository: DocumentRepository,
        settings: Settings,
    ) -> None:
        self._documents = document_repository
        self._settings = settings

    async def create_pending_document(
        self,
        *,
        project_id: UUID,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> Document:
        """Validate an upload and record it as ``pending``.

        This is the synchronous half of ingestion (design §8.1). The caller
        (the router) schedules the asynchronous pipeline against the returned
        document's id, so the upload response returns immediately — "the upload
        response must not wait on processing".

        Raises
        ------
        UnsupportedFileTypeError, FileTooLargeError
            If the upload fails the allow-list or size checks (design §9.5).
        """
        safe_filename = sanitise_filename(filename)
        mime_type = validate_upload(
            filename=safe_filename,
            content_type=content_type,
            size_bytes=len(content),
            allowed_mime_types=self._settings.allowed_upload_mime_types,
            max_size_bytes=self._settings.max_upload_bytes,
        )

        return await self._documents.create(
            project_id=project_id,
            filename=safe_filename,
            metadata={
                "title": None,
                "authors": [],
                "page_count": None,
                "mime_type": mime_type,
                "size_bytes": len(content),
                "ocr_used": False,
                "ocr_low_confidence": False,
                "ocr_min_confidence": None,
                "failure_reason": None,
            },
        )

    async def get_document(self, document_id: UUID, *, project_id: UUID) -> Document:
        """Fetch a document the caller's project owns.

        Raises
        ------
        NotFoundError
            If the document does not exist, or belongs to a different project
            (design §9.3 rule 4).
        """
        document = await self._documents.get_by_id_for_project(document_id, project_id=project_id)
        if document is None:
            raise NotFoundError("Document not found.")
        return document

    async def get_document_for_owner(self, document_id: UUID, *, owner_id: UUID) -> Document:
        """Fetch a document by id, scoped by project ownership rather than a
        project id in the path (used by ``GET /documents/{id}``, design §6.1).

        Raises
        ------
        NotFoundError
            If the document does not exist, or its project belongs to someone
            else (design §9.3 rule 4).
        """
        document = await self._documents.get_by_id_for_owner(document_id, owner_id=owner_id)
        if document is None:
            raise NotFoundError("Document not found.")
        return document

    async def list_documents(self, *, project_id: UUID) -> list[Document]:
        return await self._documents.list_for_project(project_id=project_id)

    async def delete_document(self, document_id: UUID, *, project_id: UUID) -> None:
        """Delete a document; cascades to its chunks (FR-C10)."""
        document = await self.get_document(document_id, project_id=project_id)
        await self._documents.delete(document)

    async def delete_document_for_owner(self, document_id: UUID, *, owner_id: UUID) -> None:
        """Delete a document by id, scoped by project ownership (used by
        ``DELETE /documents/{id}``, design §6.1, FR-C10)."""
        document = await self.get_document_for_owner(document_id, owner_id=owner_id)
        await self._documents.delete(document)
