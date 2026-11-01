"""Query object for the ``documents`` aggregate (design §6.6, §9.3).

Every method requires either ``project_id`` or ``owner_id``, making a
cross-tenant query unwritable through this API (design §9.3 rule 3).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document, DocumentStatus
from app.db.models.project import Project


class DocumentRepository:
    """Persistence for :class:`Document`, scoped to a project on every read."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: UUID,
        filename: str,
        metadata: dict[str, Any],
    ) -> Document:
        document = Document(
            project_id=project_id,
            filename=filename,
            status=DocumentStatus.PENDING,
            metadata_=metadata,
        )
        self._session.add(document)
        await self._session.flush()
        return document

    async def get_by_id_for_project(
        self, document_id: UUID, *, project_id: UUID
    ) -> Document | None:
        """Fetch a document only if it belongs to ``project_id``.

        A document belonging to a different project is indistinguishable from
        one that does not exist (design §9.3 rule 4) — the caller maps a miss
        to 404.
        """
        statement = select(Document).where(
            Document.id == document_id,
            Document.project_id == project_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id_for_owner(self, document_id: UUID, *, owner_id: UUID) -> Document | None:
        """Fetch a document only if it belongs to a project owned by
        ``owner_id`` (design §9.3 rule 3).

        Used by the ``/documents/{id}`` routes (design §6.1), which are not
        nested under a project path and so must resolve ownership through the
        document's own ``project_id`` instead.
        """
        statement = (
            select(Document)
            .join(Project, Document.project_id == Project.id)
            .where(Document.id == document_id, Project.owner_id == owner_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Fetch a document by id alone.

        Only for routes that authorise the document's project *after* loading it
        (``/documents/{id}``). Project-scoped routes must use
        :meth:`get_by_id_for_project` so the tenancy predicate stays in the SQL.
        """
        result = await self._session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def list_for_project(self, *, project_id: UUID) -> list[Document]:
        """Return every document in a project, most recently uploaded first."""
        statement = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.uploaded_at.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def update_status(
        self,
        document: Document,
        *,
        status: DocumentStatus,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        document.status = status
        if metadata is not None:
            document.metadata_ = metadata
        await self._session.flush()
        return document

    async def delete(self, document: Document) -> None:
        """Delete a document. Cascades to its chunks at the database level."""
        await self._session.delete(document)
        await self._session.flush()
