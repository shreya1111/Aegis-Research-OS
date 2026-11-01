"""Wire contracts for research workspaces (design §6.1, FR-B)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.project_member import ProjectRole

if TYPE_CHECKING:
    from app.db.models.project import Project


class ProjectCreate(BaseModel):
    """Payload for ``POST /projects``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ProjectRead(BaseModel):
    """Project representation returned to a caller who may access it."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    title: str
    description: str | None
    created_at: datetime
    #: The caller's effective role in this project (Phase 10). The UI uses it to
    #: hide actions the caller may not perform; the server still enforces them.
    role: ProjectRole | None = Field(
        default=None,
        description="caller's role in this project: owner, editor, or viewer",
    )

    @classmethod
    def from_model(cls, project: Project, role: ProjectRole | None = None) -> ProjectRead:
        """Build the wire view of a project for a caller holding ``role``.

        The role is passed in rather than read off the project because it comes
        from the membership graph, not the ``projects`` row.
        """
        return cls(
            id=project.id,
            title=project.title,
            description=project.description,
            created_at=project.created_at,
            role=role,
        )
