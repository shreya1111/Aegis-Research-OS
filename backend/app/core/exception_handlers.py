"""Global exception handlers — the single place error responses are produced."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.core.envelope import fail, fail_from
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger

logger = get_logger(__name__)

#: HTTP statuses raised by the framework itself (404 on an unknown path, 405 on a
#: wrong method) mapped onto the closed client-facing error code set.
_STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
}


async def handle_app_error(request: Request, exc: Exception) -> Response:
    """Map a domain exception onto the envelope.

    Client errors are logged at ``WARNING`` and server errors at ``ERROR`` — the
    distinction keeps genuine faults visible without alert noise from ordinary
    validation failures.
    """
    assert isinstance(exc, AppError)
    log = logger.warning if exc.status_code < 500 else logger.error
    log(
        "app.error",
        extra={
            "event": "app.error",
            "error_code": exc.code.value,
            "status_code": exc.status_code,
            "path": request.url.path,
            **exc.context,
        },
    )
    return fail_from(exc)


async def handle_validation_error(request: Request, exc: Exception) -> Response:
    """Translate FastAPI/Pydantic request validation failures."""
    assert isinstance(exc, RequestValidationError)
    logger.warning(
        "request.validation_failed",
        extra={
            "event": "request.validation_failed",
            "path": request.url.path,
            "error_count": len(exc.errors()),
        },
    )
    return fail(
        ErrorCode.VALIDATION_ERROR,
        "The request payload is invalid.",
        status_code=422,
    )


async def handle_http_exception(request: Request, exc: Exception) -> Response:
    """Wrap framework-raised HTTP errors in the uniform envelope."""
    assert isinstance(exc, StarletteHTTPException)
    code = _STATUS_TO_CODE.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    message = exc.detail if isinstance(exc.detail, str) and exc.detail else "Request failed."
    headers = dict(exc.headers) if exc.headers else None
    return fail(code, message, status_code=exc.status_code, headers=headers)


async def handle_unexpected_error(request: Request, exc: Exception) -> Response:
    """Last-resort handler: log everything, disclose nothing (design §6.10)."""
    logger.exception(
        "internal.error",
        extra={"event": "internal.error", "path": request.url.path},
    )
    return fail(
        ErrorCode.INTERNAL_ERROR,
        "An unexpected error occurred.",
        status_code=500,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every handler to the application instance."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)
