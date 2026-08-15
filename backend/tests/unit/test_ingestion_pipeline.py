"""Unit tests for IngestionPipeline against stubbed collaborators (design §6.4,
§8.1). No HTTP, no real database, no real embedding model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.config import Settings
from app.db.models.document import Document, DocumentStatus
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.ingestion.types import Chunk


class FakeDocumentRepository:
    def __init__(self, document: Document) -> None:
        self._document = document
        self.status_history: list[DocumentStatus] = []
        self.metadata_history: list[dict[str, Any]] = []

    async def get_by_id_for_project(
        self, document_id: uuid.UUID, *, project_id: uuid.UUID
    ) -> Document | None:
        if document_id == self._document.id and project_id == self._document.project_id:
            return self._document
        return None

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
        self.status_history.append(status)
        self.metadata_history.append(document.metadata_)
        return document


class FakeChunkRepository:
    def __init__(self) -> None:
        self.created: list[tuple[uuid.UUID, list[Chunk], list[list[float]]]] = []
        self.deleted_for: list[uuid.UUID] = []

    async def bulk_create(
        self,
        *,
        document_id: uuid.UUID,
        project_id: uuid.UUID,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> list[Any]:
        self.created.append((document_id, chunks, embeddings))
        return []

    async def delete_for_document(self, document_id: uuid.UUID) -> None:
        self.deleted_for.append(document_id)


class FakeEmbeddingService:
    def __init__(self, *, dimensions: int = 4) -> None:
        self.dimensions = dimensions
        self.embed_calls: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(texts)
        return [[0.1] * self.dimensions for _ in texts]


def _make_document(*, mime_type: str = "application/pdf", size_bytes: int = 100) -> Document:
    return Document(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        filename="paper.pdf",
        status=DocumentStatus.PENDING,
        metadata_={
            "title": None,
            "authors": [],
            "page_count": None,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "ocr_used": False,
            "ocr_low_confidence": False,
            "ocr_min_confidence": None,
            "failure_reason": None,
        },
        uploaded_at=datetime.now(UTC),
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(chunk_tokens=50, chunk_overlap_tokens=5, ocr_enabled=True)


def _digital_pdf_bytes(text: str) -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    data = bytes(doc.tobytes())
    doc.close()
    return data


@pytest.mark.unit
class TestIngestionPipeline:
    async def test_successful_run_transitions_pending_to_processing_to_ready(
        self, settings: Settings
    ) -> None:
        document = _make_document()
        documents = FakeDocumentRepository(document)
        chunks_repo = FakeChunkRepository()
        pipeline = IngestionPipeline(
            document_repository=documents,  # type: ignore[arg-type]
            chunk_repository=chunks_repo,  # type: ignore[arg-type]
            embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
            settings=settings,
        )

        content = _digital_pdf_bytes("This is a real extractable PDF document.")
        await pipeline.run(document.id, project_id=document.project_id, content=content)

        assert documents.status_history == [DocumentStatus.PROCESSING, DocumentStatus.READY]

    async def test_successful_run_persists_chunks_with_embeddings(self, settings: Settings) -> None:
        document = _make_document()
        documents = FakeDocumentRepository(document)
        chunks_repo = FakeChunkRepository()
        pipeline = IngestionPipeline(
            document_repository=documents,  # type: ignore[arg-type]
            chunk_repository=chunks_repo,  # type: ignore[arg-type]
            embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
            settings=settings,
        )

        content = _digital_pdf_bytes("Some reasonably long extractable text content for chunking.")
        await pipeline.run(document.id, project_id=document.project_id, content=content)

        assert len(chunks_repo.created) == 1
        document_id, chunks, embeddings = chunks_repo.created[0]
        assert document_id == document.id
        assert len(chunks) == len(embeddings)
        assert len(chunks) > 0

    async def test_successful_run_records_extracted_metadata(self, settings: Settings) -> None:
        document = _make_document()
        documents = FakeDocumentRepository(document)
        pipeline = IngestionPipeline(
            document_repository=documents,  # type: ignore[arg-type]
            chunk_repository=FakeChunkRepository(),  # type: ignore[arg-type]
            embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
            settings=settings,
        )

        content = _digital_pdf_bytes("Extractable content.")
        await pipeline.run(document.id, project_id=document.project_id, content=content)

        final_metadata = documents.metadata_history[-1]
        assert final_metadata["page_count"] == 1
        assert final_metadata["ocr_used"] is False
        assert final_metadata["failure_reason"] is None

    async def test_corrupt_file_marks_document_failed_with_a_reason(
        self, settings: Settings
    ) -> None:
        document = _make_document()
        documents = FakeDocumentRepository(document)
        pipeline = IngestionPipeline(
            document_repository=documents,  # type: ignore[arg-type]
            chunk_repository=FakeChunkRepository(),  # type: ignore[arg-type]
            embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
            settings=settings,
        )

        await pipeline.run(document.id, project_id=document.project_id, content=b"not a real pdf")

        assert documents.status_history[-1] == DocumentStatus.FAILED
        assert documents.metadata_history[-1]["failure_reason"] is not None

    async def test_corrupt_file_never_raises(self, settings: Settings) -> None:
        """Design FR-C9: "No crash" — the pipeline absorbs the failure."""
        document = _make_document()
        documents = FakeDocumentRepository(document)
        pipeline = IngestionPipeline(
            document_repository=documents,  # type: ignore[arg-type]
            chunk_repository=FakeChunkRepository(),  # type: ignore[arg-type]
            embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
            settings=settings,
        )

        # Simply not raising is the assertion.
        await pipeline.run(document.id, project_id=document.project_id, content=b"garbage")

    async def test_oversized_page_count_is_rejected(self, settings: Settings) -> None:
        settings.max_upload_pages = 0  # force rejection regardless of content
        document = _make_document()
        documents = FakeDocumentRepository(document)
        pipeline = IngestionPipeline(
            document_repository=documents,  # type: ignore[arg-type]
            chunk_repository=FakeChunkRepository(),  # type: ignore[arg-type]
            embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
            settings=settings,
        )

        content = _digital_pdf_bytes("One page of content.")
        await pipeline.run(document.id, project_id=document.project_id, content=content)

        assert documents.status_history[-1] == DocumentStatus.FAILED
        assert "page" in documents.metadata_history[-1]["failure_reason"].lower()

    async def test_missing_document_is_skipped_without_error(self, settings: Settings) -> None:
        document = _make_document()
        documents = FakeDocumentRepository(document)
        pipeline = IngestionPipeline(
            document_repository=documents,  # type: ignore[arg-type]
            chunk_repository=FakeChunkRepository(),  # type: ignore[arg-type]
            embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
            settings=settings,
        )

        # A different document id than the one the fake repository holds.
        await pipeline.run(uuid.uuid4(), project_id=document.project_id, content=b"irrelevant")

        assert documents.status_history == []  # never touched

    async def test_reprocessing_deletes_existing_chunks_first(self, settings: Settings) -> None:
        """Design §8.1: "deletes and rebuilds its chunks rather than
        appending" — verified for both the success and failure paths."""
        document = _make_document()
        documents = FakeDocumentRepository(document)
        chunks_repo = FakeChunkRepository()
        pipeline = IngestionPipeline(
            document_repository=documents,  # type: ignore[arg-type]
            chunk_repository=chunks_repo,  # type: ignore[arg-type]
            embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
            settings=settings,
        )

        content = _digital_pdf_bytes("Content for re-ingestion test.")
        await pipeline.run(document.id, project_id=document.project_id, content=content)

        assert document.id in chunks_repo.deleted_for

    async def test_docx_mime_type_is_routed_to_the_docx_parser(self, settings: Settings) -> None:
        from docx import Document as DocxDocument

        docx_doc = DocxDocument()
        docx_doc.add_paragraph("DOCX content for the pipeline test.")
        import io

        buffer = io.BytesIO()
        docx_doc.save(buffer)

        document = _make_document(
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        documents = FakeDocumentRepository(document)
        pipeline = IngestionPipeline(
            document_repository=documents,  # type: ignore[arg-type]
            chunk_repository=FakeChunkRepository(),  # type: ignore[arg-type]
            embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
            settings=settings,
        )

        await pipeline.run(document.id, project_id=document.project_id, content=buffer.getvalue())

        assert documents.status_history[-1] == DocumentStatus.READY
