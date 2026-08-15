"""Unit tests for AuthService against stubbed collaborators (no HTTP, no DB)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from fakeredis.aioredis import FakeRedis

from app.core.cache import TokenDenylist
from app.core.config import Settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import TokenType, decode_token, hash_password
from app.db.models.user import User
from app.services.auth_service import AuthService


class FakeUserRepository:
    """In-memory stand-in for UserRepository, keyed by email."""

    def __init__(self) -> None:
        self._by_email: dict[str, User] = {}
        self._by_id: dict[uuid.UUID, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email.lower())

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._by_id.get(user_id)

    async def create(self, *, email: str, hashed_password: str, name: str) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email.lower(),
            hashed_password=hashed_password,
            name=name,
            created_at=datetime.now(UTC),
        )
        self._by_email[user.email] = user
        self._by_id[user.id] = user
        return user

    def seed(self, *, email: str, password: str, name: str = "Seeded User") -> User:
        user = User(
            id=uuid.uuid4(),
            email=email.lower(),
            hashed_password=hash_password(password),
            name=name,
            created_at=datetime.now(UTC),
        )
        self._by_email[user.email] = user
        self._by_id[user.id] = user
        return user


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jwt_secret="unit-test-secret-value-1234567890",
        jwt_access_token_ttl_minutes=15,
        jwt_refresh_token_ttl_days=30,
    )


@pytest.fixture
async def redis() -> AsyncIterator[FakeRedis]:
    client = FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def service(repository: FakeUserRepository, redis: FakeRedis, settings: Settings) -> AuthService:
    return AuthService(
        user_repository=repository,  # type: ignore[arg-type]
        token_denylist=TokenDenylist(redis),
        settings=settings,
    )


@pytest.mark.unit
async def test_register_creates_a_user_with_a_hashed_password(
    service: AuthService, repository: FakeUserRepository
) -> None:
    user = await service.register(email="Alice@Example.com", password="correct-horse", name="Alice")

    assert user.email == "alice@example.com"
    assert user.hashed_password != "correct-horse"
    stored = await repository.get_by_email("alice@example.com")
    assert stored is not None


@pytest.mark.unit
async def test_register_rejects_a_duplicate_email(
    service: AuthService, repository: FakeUserRepository
) -> None:
    repository.seed(email="alice@example.com", password="correct-horse")

    with pytest.raises(ConflictError):
        await service.register(email="alice@example.com", password="another-pass", name="Alice2")


@pytest.mark.unit
async def test_authenticate_succeeds_with_correct_credentials(
    service: AuthService, repository: FakeUserRepository
) -> None:
    repository.seed(email="alice@example.com", password="correct-horse")

    user = await service.authenticate(email="alice@example.com", password="correct-horse")

    assert user.email == "alice@example.com"


@pytest.mark.unit
async def test_authenticate_rejects_wrong_password(
    service: AuthService, repository: FakeUserRepository
) -> None:
    repository.seed(email="alice@example.com", password="correct-horse")

    with pytest.raises(AuthenticationError):
        await service.authenticate(email="alice@example.com", password="wrong-pass")


@pytest.mark.unit
async def test_authenticate_rejects_unknown_email_with_the_same_error(
    service: AuthService,
) -> None:
    with pytest.raises(AuthenticationError) as unknown_email_error:
        await service.authenticate(email="ghost@example.com", password="whatever12")

    repository = FakeUserRepository()
    repository.seed(email="alice@example.com", password="correct-horse")
    settings = Settings(jwt_secret="unit-test-secret-value-1234567890")
    other_service = AuthService(
        user_repository=repository,  # type: ignore[arg-type]
        token_denylist=TokenDenylist(FakeRedis(decode_responses=True)),
        settings=settings,
    )
    with pytest.raises(AuthenticationError) as wrong_password_error:
        await other_service.authenticate(email="alice@example.com", password="wrong-pass")

    # Login is not a user-enumeration oracle (design §9.1): identical message.
    assert str(unknown_email_error.value) == str(wrong_password_error.value)


@pytest.mark.unit
async def test_issue_token_pair_produces_a_valid_access_and_refresh_token(
    service: AuthService, settings: Settings
) -> None:
    user_id = uuid.uuid4()

    pair = service.issue_token_pair(user_id)

    access_payload = decode_token(
        pair.access_token, secret=settings.jwt_secret, expected_type=TokenType.ACCESS
    )
    refresh_payload = decode_token(
        pair.refresh_token, secret=settings.jwt_secret, expected_type=TokenType.REFRESH
    )
    assert access_payload.sub == user_id
    assert refresh_payload.sub == user_id
    assert access_payload.jti != refresh_payload.jti


@pytest.mark.unit
async def test_refresh_access_token_issues_a_new_access_token(
    service: AuthService, settings: Settings
) -> None:
    user_id = uuid.uuid4()
    pair = service.issue_token_pair(user_id)

    new_access = await service.refresh_access_token(pair.refresh_token)

    payload = decode_token(
        new_access.access_token, secret=settings.jwt_secret, expected_type=TokenType.ACCESS
    )
    assert payload.sub == user_id


@pytest.mark.unit
async def test_refresh_access_token_rejects_an_access_token(service: AuthService) -> None:
    user_id = uuid.uuid4()
    pair = service.issue_token_pair(user_id)

    with pytest.raises(AuthenticationError):
        await service.refresh_access_token(pair.access_token)


@pytest.mark.unit
async def test_resolve_current_user_returns_the_token_subject(
    service: AuthService, repository: FakeUserRepository
) -> None:
    user = repository.seed(email="alice@example.com", password="correct-horse")
    pair = service.issue_token_pair(user.id)

    resolved = await service.resolve_current_user(pair.access_token)

    assert resolved.id == user.id


@pytest.mark.unit
async def test_resolve_current_user_rejects_a_token_for_a_deleted_user(
    service: AuthService,
) -> None:
    pair = service.issue_token_pair(uuid.uuid4())

    with pytest.raises(AuthenticationError):
        await service.resolve_current_user(pair.access_token)


@pytest.mark.unit
async def test_logout_revokes_the_access_token(
    service: AuthService, repository: FakeUserRepository
) -> None:
    user = repository.seed(email="alice@example.com", password="correct-horse")
    pair = service.issue_token_pair(user.id)

    await service.logout(pair.access_token)

    with pytest.raises(AuthenticationError):
        await service.resolve_current_user(pair.access_token)


@pytest.mark.unit
async def test_logout_does_not_affect_other_tokens(
    service: AuthService, repository: FakeUserRepository
) -> None:
    user = repository.seed(email="alice@example.com", password="correct-horse")
    first_pair = service.issue_token_pair(user.id)
    second_pair = service.issue_token_pair(user.id)

    await service.logout(first_pair.access_token)

    resolved = await service.resolve_current_user(second_pair.access_token)
    assert resolved.id == user.id


@pytest.mark.unit
async def test_expired_access_token_is_rejected_before_denylist_lookup(
    repository: FakeUserRepository, redis: FakeRedis
) -> None:
    from app.core.security import create_access_token

    settings = Settings(jwt_secret="unit-test-secret-value-1234567890")
    service = AuthService(
        user_repository=repository,  # type: ignore[arg-type]
        token_denylist=TokenDenylist(redis),
        settings=settings,
    )
    token = create_access_token(
        uuid.uuid4(),
        secret=settings.jwt_secret,
        expires_delta=timedelta(seconds=-1),
        jti=str(uuid.uuid4()),
    )

    with pytest.raises(AuthenticationError):
        await service.resolve_current_user(token)
