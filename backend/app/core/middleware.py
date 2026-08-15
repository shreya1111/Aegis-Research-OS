"""Cross-cutting HTTP middleware: correlation IDs, access logs, security headers."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.logging import get_logger, request_id_var

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

RequestHandler = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, expose it, and emit one structured access log line.

    The identifier is echoed in the response header so a user-reported failure can
    be correlated with server logs (design §6.10, §14.6).
    """

    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming if incoming else str(uuid.uuid4())
        token = request_id_var.set(request_id)
        request.state.request_id = request_id

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # The global exception handlers own the response shape; this log line
            # exists so unhandled failures are still attributable to a request.
            logger.exception(
                "http.request.failed",
                extra={
                    "event": "http.request.failed",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            raise
        finally:
            request_id_var.reset(token)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "http.request.completed",
            extra={
                "event": "http.request.completed",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply defence-in-depth response headers (design §9.4).

    The reverse proxy sets these in staging and production; applying them here as
    well means local development and direct-to-backend traffic are covered too.
    ``Strict-Transport-Security`` is only meaningful over TLS, so it is emitted
    exclusively when the deployment is HTTPS-terminated.
    """

    def __init__(self, app: ASGIApp, *, enable_hsts: bool) -> None:
        super().__init__(app)
        self._enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        response = await call_next(request)
        headers = MutableHeaders(scope=None, raw=response.raw_headers)
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "no-referrer"
        headers["Cross-Origin-Opener-Policy"] = "same-origin"
        headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        headers.setdefault("Cache-Control", "no-store")
        if self._enable_hsts:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
