"""``/projects/{id}/documents`` and ``/documents/{id}`` routers (design §6.5, FR-C)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, UploadFile, status

from app.api.deps import CurrentUserDep, DbSessionDep, DocumentServiceDep
from app.api.v1.deps import ProjectInScopeDep
from app.core.envelope import ok
from app.schemas.common import ApiResponse
from app.schemas.document import DocumentRead
from app.services.ingestion.runner import run_ingestion as run_ingestion_pipeline

router = APIRouter(tags=["documents"])

UploadedFile = Annotated[UploadFile, File(...)]


@router.post(
    "/projects/{project_id}/documents",
    response_model=ApiResponse[DocumentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document for ingestion",
)
async def upload_document(
    project: ProjectInScopeDep,
    background_tasks: BackgroundTasks,
    document_service: DocumentServiceDep,
    session: DbSessionDep,
    file: UploadedFile,
) -> ApiResponse[DocumentRead]:
    content = await file.read()

    document = await document_service.create_pending_document(
        project_id=project.id,
        filename=file.filename or "upload",
        content_type=file.content_type,
        content=content,
    )

    # Commit the pending row before scheduling the background task. Since
    # FastAPI 0.106, ``yield``-dependency teardown (where the request session
    # would otherwise commit) runs *after* background tasks — so without this
    # explicit commit the ingestion task's fresh session cannot see the row
    # yet (design §6.7: background jobs are "status-observable from the
    # database"; the row must be durable before dispatch).
    await session.commit()

    # ``run_ingestion_pipeline`` is a coroutine function passed with its
    # arguments, so FastAPI awaits it correctly after the response is sent.
    background_tasks.add_task(run_ingestion_pipeline, document.id, project.id, content)

    return ok(DocumentRead.from_model(document))


@router.get(
    "/projects/{project_id}/documents",
    response_model=ApiResponse[list[DocumentRead]],
    summary="List documents in a project",
)
async def list_documents(
    project: ProjectInScopeDep,
    document_service: DocumentServiceDep,
) -> ApiResponse[list[DocumentRead]]:
    documents = await document_service.list_documents(project_id=project.id)
    return ok([DocumentRead.from_model(document) for document in documents])


@router.get(
    "/documents/{document_id}",
    response_model=ApiResponse[DocumentRead],
    summary="Get document detail and processing status",
)
async def get_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
) -> ApiResponse[DocumentRead]:
    document = await document_service.get_document_for_owner(document_id, owner_id=current_user.id)
    return ok(DocumentRead.from_model(document))


@router.delete(
    "/documents/{document_id}",
    response_model=ApiResponse[None],
    summary="Delete a document and its chunks",
)
async def delete_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
) -> ApiResponse[None]:
    await document_service.delete_document_for_owner(document_id, owner_id=current_user.id)
    return ok(None)
