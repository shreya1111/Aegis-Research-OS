"""Uniform response envelope and pagination contracts (design §6.1)."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import ErrorCode

DataT = TypeVar("DataT")
ItemT = TypeVar("ItemT")


class ErrorDetail(BaseModel):
    """Machine-readable code plus a safe, human-readable message."""

    model_config = ConfigDict(frozen=True)

    code: ErrorCode
    message: str


class ApiResponse(BaseModel, Generic[DataT]):
    """Every endpoint — success or failure — responds with this shape."""

    model_config = ConfigDict(frozen=True)

    success: bool
    data: DataT | None = None
    error: ErrorDetail | None = None


class Page(BaseModel, Generic[ItemT]):
    """Paginated payload placed in ``data`` for list endpoints."""

    model_config = ConfigDict(frozen=True)

    items: list[ItemT]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class PaginationParams(BaseModel):
    """Query parameters shared by every list endpoint."""

    model_config = ConfigDict(frozen=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class HealthStatus(BaseModel):
    """Liveness payload returned by the unauthenticated health endpoint."""

    model_config = ConfigDict(frozen=True)

    status: str
    service: str
    version: str
    environment: str
