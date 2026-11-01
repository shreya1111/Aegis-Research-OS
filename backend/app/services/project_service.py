"""Project CRUD and ownership-scoped access (design §6.4, FR-B)."""

from __future__ import annotations

from uuid import UUID

from app.core.errors import NotFoundError
from app.db.models.project import Project
from app.db.repositories.project_repository import ProjectRepository


class ProjectService:
    """Business logic for research workspaces.

    Ownership is the only authority in the MVP (design §9.3): every method here
    takes the caller's ``owner_id`` and never returns a project outside that
    scope.
    """

    def __init__(self, *, project_repository: ProjectRepository) -> None:
        self._projects = project_repository

    async def create_project(
        self, *, owner_id: UUID, title: str, description: str | None
    ) -> Project:
        return await self._projects.create(owner_id=owner_id, title=title, description=description)

    async def list_projects(
        self, *, owner_id: UUID, page: int, page_size: int
    ) -> tuple[list[Project], int]:
        """One page of the projects ``owner_id`` may access.

        Phase 10 widens this from ownership to membership (FR-B2: "lists only
        projects the caller may access"), so an invited user finds the shared
        workspace on their dashboard. The parameter keeps its historical name to
        avoid churning every call site; it is the *caller*, not the owner.
        """
        offset = (page - 1) * page_size
        return await self._projects.list_for_member(
            user_id=owner_id, offset=offset, limit=page_size
        )

    async def get_project(self, project_id: UUID, *, owner_id: UUID) -> Project:
        """Fetch a project the caller owns.

        Raises
        ------
        NotFoundError
            If the project does not exist, or exists but is owned by someone
            else — the two cases are indistinguishable to the caller
            (design §9.3 rule 4, FR-B3).
        """
        project = await self._projects.get_by_id_for_owner(project_id, owner_id=owner_id)
        if project is None:
            raise NotFoundError("Project not found.")
        return project

    async def get_project_for_member(self, project_id: UUID, *, user_id: UUID) -> Project:
        """Fetch a project the caller may access as owner or invited member.

        Raises
        ------
        NotFoundError
            If the project does not exist, or the caller reaches it through
            neither ownership nor membership — the cases stay indistinguishable
            (design §9.3 rule 4, FR-B3).
        """
        project = await self._projects.get_by_id_for_member(project_id, user_id=user_id)
        if project is None:
            raise NotFoundError("Project not found.")
        return project

    async def delete_project(self, project_id: UUID, *, owner_id: UUID) -> None:
        """Delete a project the caller owns; cascades to all its content (FR-B4)."""
        project = await self.get_project(project_id, owner_id=owner_id)
        await self._projects.delete(project)
