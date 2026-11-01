"""Unit tests for ProjectService against a stubbed repository (no HTTP, no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.core.errors import NotFoundError
from app.db.models.project import Project
from app.services.project_service import ProjectService


class FakeProjectRepository:
    """In-memory stand-in for ProjectRepository."""

    def __init__(self) -> None:
        self._projects: dict[uuid.UUID, Project] = {}
        #: project id → user ids invited as members (Phase 10, FR-A).
        self._members: dict[uuid.UUID, set[uuid.UUID]] = {}

    def add_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self._members.setdefault(project_id, set()).add(user_id)

    def _can_access(self, project: Project, user_id: uuid.UUID) -> bool:
        return project.owner_id == user_id or user_id in self._members.get(project.id, set())

    async def create(self, *, owner_id: uuid.UUID, title: str, description: str | None) -> Project:
        project = Project(
            id=uuid.uuid4(),
            owner_id=owner_id,
            title=title,
            description=description,
            created_at=datetime.now(UTC),
        )
        self._projects[project.id] = project
        return project

    async def get_by_id_for_owner(
        self, project_id: uuid.UUID, *, owner_id: uuid.UUID
    ) -> Project | None:
        project = self._projects.get(project_id)
        if project is None or project.owner_id != owner_id:
            return None
        return project

    async def get_by_id_for_member(
        self, project_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> Project | None:
        project = self._projects.get(project_id)
        if project is None or not self._can_access(project, user_id):
            return None
        return project

    async def list_for_owner(
        self, *, owner_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[Project], int]:
        owned = [p for p in self._projects.values() if p.owner_id == owner_id]
        owned.sort(key=lambda p: p.created_at, reverse=True)
        total = len(owned)
        return owned[offset : offset + limit], total

    async def list_for_member(
        self, *, user_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[Project], int]:
        accessible = [p for p in self._projects.values() if self._can_access(p, user_id)]
        accessible.sort(key=lambda p: p.created_at, reverse=True)
        total = len(accessible)
        return accessible[offset : offset + limit], total

    async def delete(self, project: Project) -> None:
        self._projects.pop(project.id, None)


@pytest.fixture
def repository() -> FakeProjectRepository:
    return FakeProjectRepository()


@pytest.fixture
def service(repository: FakeProjectRepository) -> ProjectService:
    return ProjectService(project_repository=repository)  # type: ignore[arg-type]


@pytest.mark.unit
async def test_create_project_stores_the_owner(service: ProjectService) -> None:
    owner_id = uuid.uuid4()

    project = await service.create_project(owner_id=owner_id, title="Thesis", description=None)

    assert project.owner_id == owner_id
    assert project.title == "Thesis"


@pytest.mark.unit
async def test_get_project_returns_the_owners_project(service: ProjectService) -> None:
    owner_id = uuid.uuid4()
    created = await service.create_project(owner_id=owner_id, title="Thesis", description=None)

    fetched = await service.get_project(created.id, owner_id=owner_id)

    assert fetched.id == created.id


@pytest.mark.unit
async def test_get_project_raises_not_found_for_a_different_owner(
    service: ProjectService,
) -> None:
    owner_id = uuid.uuid4()
    other_owner_id = uuid.uuid4()
    created = await service.create_project(owner_id=owner_id, title="Thesis", description=None)

    with pytest.raises(NotFoundError):
        await service.get_project(created.id, owner_id=other_owner_id)


@pytest.mark.unit
async def test_get_project_raises_not_found_for_a_nonexistent_project(
    service: ProjectService,
) -> None:
    with pytest.raises(NotFoundError):
        await service.get_project(uuid.uuid4(), owner_id=uuid.uuid4())


@pytest.mark.unit
async def test_cross_tenant_lookup_and_missing_lookup_raise_the_same_error(
    service: ProjectService,
) -> None:
    """Existence must not be disclosed (design §9.3 rule 4, FR-B3)."""
    owner_id = uuid.uuid4()
    other_owner_id = uuid.uuid4()
    created = await service.create_project(owner_id=owner_id, title="Thesis", description=None)

    with pytest.raises(NotFoundError) as cross_tenant:
        await service.get_project(created.id, owner_id=other_owner_id)
    with pytest.raises(NotFoundError) as missing:
        await service.get_project(uuid.uuid4(), owner_id=other_owner_id)

    assert str(cross_tenant.value) == str(missing.value)


@pytest.mark.unit
async def test_list_projects_returns_only_the_owners_projects(
    service: ProjectService,
) -> None:
    owner_id = uuid.uuid4()
    other_owner_id = uuid.uuid4()
    await service.create_project(owner_id=owner_id, title="Mine", description=None)
    await service.create_project(owner_id=other_owner_id, title="Not mine", description=None)

    projects, total = await service.list_projects(owner_id=owner_id, page=1, page_size=10)

    assert total == 1
    assert projects[0].title == "Mine"


@pytest.mark.unit
async def test_list_projects_paginates(service: ProjectService) -> None:
    owner_id = uuid.uuid4()
    for index in range(5):
        await service.create_project(owner_id=owner_id, title=f"Project {index}", description=None)

    page_one, total = await service.list_projects(owner_id=owner_id, page=1, page_size=2)
    page_two, _ = await service.list_projects(owner_id=owner_id, page=2, page_size=2)

    assert total == 5
    assert len(page_one) == 2
    assert len(page_two) == 2
    assert {p.id for p in page_one}.isdisjoint({p.id for p in page_two})


@pytest.mark.unit
async def test_delete_project_removes_it_for_the_owner(service: ProjectService) -> None:
    owner_id = uuid.uuid4()
    created = await service.create_project(owner_id=owner_id, title="Thesis", description=None)

    await service.delete_project(created.id, owner_id=owner_id)

    with pytest.raises(NotFoundError):
        await service.get_project(created.id, owner_id=owner_id)


@pytest.mark.unit
async def test_delete_project_raises_not_found_for_a_different_owner(
    service: ProjectService,
) -> None:
    owner_id = uuid.uuid4()
    other_owner_id = uuid.uuid4()
    created = await service.create_project(owner_id=owner_id, title="Thesis", description=None)

    with pytest.raises(NotFoundError):
        await service.delete_project(created.id, owner_id=other_owner_id)
