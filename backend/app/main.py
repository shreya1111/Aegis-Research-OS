"""Application factory.

Wires configuration, logging, middleware, exception handlers, and routers. Kept
free of business logic so the composition order stays readable.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware

logger = get_logger(__name__)


def _build_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Bind startup/shutdown logging to a specific settings instance."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "app.startup",
            extra={
                "event": "app.startup",
                "environment": settings.environment,
                "version": settings.version,
            },
        )
        yield
        logger.info("app.shutdown", extra={"event": "app.shutdown"})

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    """Compose the FastAPI application.

    Accepts an optional ``settings`` override so tests can build an app with a
    different configuration without mutating process environment state.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        summary="Autonomous multi-agent AI research assistant.",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=_build_lifespan(settings),
    )
    app.state.settings = settings

    # Middleware executes in reverse registration order, so the request-context
    # middleware is added last to ensure it wraps everything else.
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.environment != "development")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
