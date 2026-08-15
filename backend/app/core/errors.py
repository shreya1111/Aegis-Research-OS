"""Domain exception hierarchy and its HTTP mapping (design §6.10).

Handlers never construct error responses by hand: they raise an :class:`AppError`
subclass and a single global handler maps it to the uniform envelope. ``error.code``
is a closed enum so clients can branch on it safely.
"""

from __future__ import annotations

from enum import StrEnum
from http import HTTPStatus
from typing import Any


class ErrorCode(StrEnum):
    """Closed set of machine-readable error codes returned to clients."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    EXPORT_FAILED = "EXPORT_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Base class for every expected failure.

    Attributes
    ----------
    code:
        Stable, machine-readable identifier surfaced to the client.
    message:
        Human-readable, safe-to-display explanation. Must never contain
        internal detail, provider payloads, or stack information.
    status_code:
        HTTP status the global handler will emit.
    context:
        Structured detail for logs only. Never serialised into the response.
    """

    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or type(self).message
        self.context = context or {}
        super().__init__(self.message)


class ValidationError(AppError):
    """Request or domain payload failed validation."""

    code = ErrorCode.VALIDATION_ERROR
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    message = "The request payload is invalid."


class AuthenticationError(AppError):
    """Credentials are absent, malformed, or expired."""

    code = ErrorCode.UNAUTHENTICATED
    status_code = HTTPStatus.UNAUTHORIZED
    message = "Authentication is required."


class PermissionDeniedError(AppError):
    """Caller is authenticated but not permitted to perform the action."""

    code = ErrorCode.FORBIDDEN
    status_code = HTTPStatus.FORBIDDEN
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    """Resource does not exist, or exists outside the caller's scope.

    Deliberately indistinguishable from "unauthorised" so the API does not
    disclose the existence of resources the caller cannot see (design §6.3).
    """

    code = ErrorCode.NOT_FOUND
    status_code = HTTPStatus.NOT_FOUND
    message = "The requested resource was not found."


class ConflictError(AppError):
    """Request conflicts with existing state, e.g. a duplicate email."""

    code = ErrorCode.CONFLICT
    status_code = HTTPStatus.CONFLICT
    message = "The resource already exists."


class RateLimitError(AppError):
    """Caller exceeded a configured rate limit or usage quota."""

    code = ErrorCode.RATE_LIMITED
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    message = "Too many requests. Please retry later."


class UnsupportedFileTypeError(AppError):
    """Upload rejected because its type is not on the allow-list."""

    code = ErrorCode.UNSUPPORTED_FILE_TYPE
    status_code = HTTPStatus.BAD_REQUEST
    message = "This file type is not supported."


class FileTooLargeError(AppError):
    """Upload rejected because it exceeds the configured size limit."""

    code = ErrorCode.FILE_TOO_LARGE
    status_code = HTTPStatus.BAD_REQUEST
    message = "The uploaded file is too large."


class LLMProviderError(AppError):
    """The active LLM provider failed in a way the run could not absorb."""

    code = ErrorCode.LLM_PROVIDER_ERROR
    status_code = HTTPStatus.BAD_GATEWAY
    message = "The language model provider is currently unavailable."


class ExportError(AppError):
    """Artifact export rendering failed for the requested format."""

    code = ErrorCode.EXPORT_FAILED
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    message = "The report could not be exported."
