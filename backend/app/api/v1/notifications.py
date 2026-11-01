"""``/notifications`` — the signed-in user's in-app inbox (Phase 10, FR-H8).

Notifications are per-user rather than per-project, so these routes are the one
place in the API that is scoped by account alone. Every read and write is
filtered by ``user_id`` in the query, never by an id supplied by the client.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, NotificationServiceDep
from app.core.envelope import ok
from app.schemas.common import ApiResponse
from app.schemas.notification import NotificationInbox, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=ApiResponse[NotificationInbox],
    summary="List the caller's notifications and unread count",
)
async def list_notifications(
    current_user: CurrentUserDep,
    notification_service: NotificationServiceDep,
) -> ApiResponse[NotificationInbox]:
    items = await notification_service.list_for_user(user_id=current_user.id)
    unread = await notification_service.unread_count(user_id=current_user.id)
    return ok(
        NotificationInbox(
            items=[NotificationRead.from_model(item) for item in items],
            unread=unread,
        )
    )


@router.post(
    "/{notification_id}/read",
    response_model=ApiResponse[None],
    summary="Mark a notification as read",
)
async def mark_read(
    notification_id: UUID,
    current_user: CurrentUserDep,
    notification_service: NotificationServiceDep,
) -> ApiResponse[None]:
    await notification_service.mark_read(notification_id, user_id=current_user.id)
    return ok(None)
