"""Wire contracts for research workspaces (design §6.1, FR-B)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Payload for ``POST /projects``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ProjectRead(BaseModel):
    """Project representation returned to the owner."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    title: str
    description: str | None
    created_at: datetime
