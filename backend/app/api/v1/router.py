"""Aggregate router for API v1.

Feature routers are registered here as each phase delivers them, so
``app.main`` never needs to change when the API surface grows.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.activity import router as activity_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.graph import router as graph_router
from app.api.v1.members import router as members_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.projects import router as projects_router
from app.api.v1.query import router as query_router
from app.api.v1.reports import router as reports_router
from app.api.v1.traces import router as traces_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(members_router)
api_router.include_router(activity_router)
api_router.include_router(documents_router)
api_router.include_router(query_router)
api_router.include_router(reports_router)
api_router.include_router(traces_router)
api_router.include_router(graph_router)
api_router.include_router(analytics_router)
api_router.include_router(notifications_router)
