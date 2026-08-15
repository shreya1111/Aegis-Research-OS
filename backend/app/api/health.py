"""Unauthenticated health endpoint (design §6.5, §11.6).

Mounted at the application root rather than under the version prefix: deployment
probes should not have to track API versions.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.envelope import ok
from app.schemas.common import ApiResponse, HealthStatus

router = APIRouter(tags=["health"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get(
    "/health",
    response_model=ApiResponse[HealthStatus],
    summary="Liveness probe",
)
async def health(settings: SettingsDep) -> ApiResponse[HealthStatus]:
    """Report that the process is up and which build/environment is serving."""
    return ok(
        HealthStatus(
            status="ok",
            service=settings.project_name,
            version=settings.version,
            environment=settings.environment,
        )
    )
