"""Aggregate router for API v1.

Feature routers are registered here as each phase delivers them, so
``app.main`` never needs to change when the API surface grows.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.projects import router as projects_router
from app.api.v1.query import router as query_router
from app.api.v1.traces import router as traces_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(documents_router)
api_router.include_router(query_router)
api_router.include_router(traces_router)
