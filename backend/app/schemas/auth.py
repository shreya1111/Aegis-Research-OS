"""Wire contracts for authentication (design §6.1, FR-A)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import get_settings


class RegisterRequest(BaseModel):
    """Payload for ``POST /auth/register``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=200)

    @field_validator("password")
    @classmethod
    def _enforce_minimum_length(cls, value: str) -> str:
        # The absolute floor is validated structurally above; the configured,
        # potentially stricter policy is enforced here (design §9.1).
        minimum = get_settings().password_min_length
        if len(value) < minimum:
            raise ValueError(f"Password must be at least {minimum} characters long.")
        return value


class LoginRequest(BaseModel):
    """Payload for ``POST /auth/login``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Payload for ``POST /auth/refresh``."""

    refresh_token: str = Field(min_length=1)


class UserProfile(BaseModel):
    """Public-facing user representation. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    email: str
    name: str
    created_at: datetime


class TokenPair(BaseModel):
    """Access + refresh tokens returned on successful login or refresh."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 — OAuth2 scheme name, not a secret


class AccessToken(BaseModel):
    """A freshly minted access token, returned by ``/auth/refresh``."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str = "bearer"  # noqa: S105 — OAuth2 scheme name, not a secret
