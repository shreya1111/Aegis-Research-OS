"""Password hashing and JWT issuance/verification (design §9.1, §9.2).

This module is the only place bcrypt and JWT primitives are touched. Services
depend on the functions here rather than on ``bcrypt``/``jwt`` directly, which
keeps the cryptographic surface auditable in one file.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from pydantic import BaseModel

from app.core.errors import AuthenticationError

#: Algorithm is pinned server-side — the client never selects it — which
#: forecloses algorithm-confusion attacks (design §9.2).
_JWT_ALGORITHM = "HS256"


class TokenType(StrEnum):
    """Discriminates access from refresh tokens so one cannot be used as the other."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    """Decoded, validated claims from a verified token."""

    sub: UUID
    type: TokenType
    exp: datetime
    jti: str


def hash_password(plain_password: str) -> str:
    """Hash a password with bcrypt using a fresh per-password salt."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time comparison of a plaintext password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # A malformed stored hash must never raise into the auth flow; it is
        # indistinguishable from a wrong password to the caller.
        return False


def _encode(
    *,
    subject: UUID,
    token_type: TokenType,
    expires_delta: timedelta,
    secret: str,
    jti: str,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "jti": jti,
    }
    return jwt.encode(claims, secret, algorithm=_JWT_ALGORITHM)


def create_access_token(
    subject: UUID,
    *,
    secret: str,
    expires_delta: timedelta,
    jti: str,
) -> str:
    """Issue a short-lived access token carrying the user id as ``sub``."""
    return _encode(
        subject=subject,
        token_type=TokenType.ACCESS,
        expires_delta=expires_delta,
        secret=secret,
        jti=jti,
    )


def create_refresh_token(
    subject: UUID,
    *,
    secret: str,
    expires_delta: timedelta,
    jti: str,
) -> str:
    """Issue a longer-lived refresh token, redeemable only at ``/auth/refresh``."""
    return _encode(
        subject=subject,
        token_type=TokenType.REFRESH,
        expires_delta=expires_delta,
        secret=secret,
        jti=jti,
    )


def decode_token(
    token: str,
    *,
    secret: str,
    expected_type: TokenType,
) -> TokenPayload:
    """Verify signature, expiry, and token type; return typed claims.

    Raises
    ------
    AuthenticationError
        If the token is malformed, expired, mistyped, or fails signature checks.
        The message is deliberately generic — token failure detail belongs in
        logs, never in the response (design §6.10).
    """
    try:
        raw = jwt.decode(token, secret, algorithms=[_JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    try:
        payload = TokenPayload.model_validate(raw)
    except Exception as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    if payload.type is not expected_type:
        raise AuthenticationError("Invalid or expired token.")

    return payload
