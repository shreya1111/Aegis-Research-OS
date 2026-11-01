"""``/projects/{id}/documents`` and ``/documents/{id}`` routers (design §6.5, FR-C)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, UploadFile, status

from app.api.deps import (
    ActivityServiceDep,
    CurrentUserDep,
    DbSessionDep,
    DocumentServiceDep,
    MembershipServiceDep,
    ProjectServiceDep,
)
from app.api.v1.deps import ProjectEditorDep, ProjectInScopeDep, resolve_project_access
from app.core.envelope import ok
from app.core.errors import PermissionDeniedError
from app.db.models.activity import ActivityAction
from app.db.models.project_member import ProjectRole
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
    project: ProjectEditorDep,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
    activity_service: ActivityServiceDep,
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
    await activity_service.record(
        project_id=project.id,
        user_id=current_user.id,
        action=ActivityAction.DOCUMENT_UPLOADED,
        entity_type="document",
        entity_id=document.id,
        context={"filename": document.filename},
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
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[DocumentRead]:
    document = await document_service.get_document_by_id(document_id)
    # Authorise through the document's own project so an invited member can poll
    # status for a document they can see, while a stranger still gets a 404.
    await resolve_project_access(
        document.project_id,
        user_id=current_user.id,
        project_service=project_service,
        membership_service=membership_service,
    )
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
    activity_service: ActivityServiceDep,
    project_service: ProjectServiceDep,
    membership_service: MembershipServiceDep,
) -> ApiResponse[None]:
    document = await document_service.get_document_by_id(document_id)
    context = await resolve_project_access(
        document.project_id,
        user_id=current_user.id,
        project_service=project_service,
        membership_service=membership_service,
    )
    if not context.role.at_least(ProjectRole.EDITOR):
        raise PermissionDeniedError("This action requires the editor role on this project.")

    filename = document.filename
    await document_service.delete_document(document.id, project_id=document.project_id)
    await activity_service.record(
        project_id=context.project.id,
        user_id=current_user.id,
        action=ActivityAction.DOCUMENT_DELETED,
        entity_type="document",
        entity_id=document_id,
        context={"filename": filename},
    )
    return ok(None)
