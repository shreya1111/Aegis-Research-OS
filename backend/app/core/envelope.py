"""Helpers that build the uniform response envelope (design §6.1).

Route handlers return ``ok(...)``; the global exception handlers return
``fail(...)``. Nothing else in the codebase constructs the envelope by hand.
"""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.errors import AppError, ErrorCode
from app.schemas.common import ApiResponse, ErrorDetail, Page

DataT = TypeVar("DataT")
ItemT = TypeVar("ItemT")


def ok(data: DataT) -> ApiResponse[DataT]:
    """Wrap a successful payload."""
    return ApiResponse[DataT](success=True, data=data, error=None)


def paginated(
    items: list[ItemT],
    *,
    total: int,
    page: int,
    page_size: int,
) -> ApiResponse[Page[ItemT]]:
    """Wrap a paginated collection as ``data.items`` + ``data.total``."""
    return ok(Page[ItemT](items=items, total=total, page=page, page_size=page_size))


def fail(
    code: ErrorCode,
    message: str,
    *,
    status_code: int,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build an error response with an empty ``data`` field."""
    body: ApiResponse[Any] = ApiResponse(
        success=False,
        data=None,
        error=ErrorDetail(code=code, message=message),
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        headers=headers,
    )


def fail_from(error: AppError, *, headers: dict[str, str] | None = None) -> JSONResponse:
    """Build an error response directly from a domain exception."""
    return fail(
        error.code,
        error.message,
        status_code=error.status_code,
        headers=headers,
    )
