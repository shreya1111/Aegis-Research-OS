"""Registration, credential verification, and token lifecycle (design §6.4, FR-A).

HTTP-free: this service is exercised directly in unit tests with a stubbed
repository and denylist, and is the only place ``UserRepository`` is driven for
authentication purposes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.cache import TokenDenylist
from app.core.config import Settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import AccessToken, TokenPair

#: Message shown for both "unknown email" and "wrong password" so login is not
#: a user-enumeration oracle (design §9.1).
_INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."


class AuthService:
    """Business logic for account creation, login, refresh, and logout."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        token_denylist: TokenDenylist,
        settings: Settings,
    ) -> None:
        self._users = user_repository
        self._denylist = token_denylist
        self._settings = settings

    async def register(self, *, email: str, password: str, name: str) -> User:
        """Create a new account.

        Raises
        ------
        ConflictError
            If the email is already registered (design FR-A1).
        """
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise ConflictError("An account with this email already exists.")

        return await self._users.create(
            email=email,
            hashed_password=hash_password(password),
            name=name,
        )

    async def authenticate(self, *, email: str, password: str) -> User:
        """Verify credentials and return the matching user.

        Raises
        ------
        AuthenticationError
            On any credential mismatch, with an identical message regardless
            of whether the email exists (design §9.1).
        """
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError(_INVALID_CREDENTIALS_MESSAGE)
        return user

    def issue_token_pair(self, user_id: UUID) -> TokenPair:
        """Mint a fresh access + refresh token pair for an authenticated user."""
        access_token = create_access_token(
            user_id,
            secret=self._settings.jwt_secret,
            expires_delta=timedelta(minutes=self._settings.jwt_access_token_ttl_minutes),
            jti=str(uuid.uuid4()),
        )
        refresh_token = create_refresh_token(
            user_id,
            secret=self._settings.jwt_secret,
            expires_delta=timedelta(days=self._settings.jwt_refresh_token_ttl_days),
            jti=str(uuid.uuid4()),
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> AccessToken:
        """Exchange a valid refresh token for a new access token (FR-A4).

        The refresh token itself is not reissued and is not checked against the
        denylist: only access tokens are revocable in the MVP (design §9.2).
        """
        payload = decode_token(
            refresh_token,
            secret=self._settings.jwt_secret,
            expected_type=TokenType.REFRESH,
        )
        access_token = create_access_token(
            payload.sub,
            secret=self._settings.jwt_secret,
            expires_delta=timedelta(minutes=self._settings.jwt_access_token_ttl_minutes),
            jti=str(uuid.uuid4()),
        )
        return AccessToken(access_token=access_token)

    async def resolve_current_user(self, access_token: str) -> User:
        """Verify an access token and load its subject.

        Raises
        ------
        AuthenticationError
            If the token is invalid, expired, revoked, or its subject no
            longer exists.
        """
        payload = decode_token(
            access_token,
            secret=self._settings.jwt_secret,
            expected_type=TokenType.ACCESS,
        )

        if await self._denylist.is_revoked(payload.jti):
            raise AuthenticationError("Invalid or expired token.")

        user = await self._users.get_by_id(payload.sub)
        if user is None:
            raise AuthenticationError("Invalid or expired token.")
        return user

    async def logout(self, access_token: str) -> None:
        """Revoke an access token by adding its ``jti`` to the denylist.

        The denylist entry's TTL matches the token's remaining lifetime, so it
        never outlives the token it protects against (design §9.2).
        """
        payload = decode_token(
            access_token,
            secret=self._settings.jwt_secret,
            expected_type=TokenType.ACCESS,
        )
        remaining = payload.exp - datetime.now(UTC)
        await self._denylist.revoke(payload.jti, ttl_seconds=max(int(remaining.total_seconds()), 0))
