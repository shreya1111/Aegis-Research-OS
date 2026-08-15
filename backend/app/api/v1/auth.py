"""``/auth`` router: register, login, refresh, me, logout (design §6.5, FR-A)."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import (
    AuthServiceDep,
    BearerTokenRequiredDep,
    CurrentUserDep,
    RateLimiterDep,
    SettingsDep,
)
from app.core.envelope import ok
from app.core.errors import RateLimitError
from app.schemas.auth import (
    AccessToken,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserProfile,
)
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_identifier(request: Request) -> str:
    """Best-effort caller identity for rate limiting (design §9.6).

    Falls back to a constant when the client host cannot be determined (for
    example, under certain test transports), which degrades the limiter to a
    single shared bucket rather than raising.
    """
    if request.client is not None:
        return request.client.host
    return "unknown"


async def _enforce_rate_limit(
    *, rate_limiter: RateLimiterDep, scope: str, identifier: str, limit: int
) -> None:
    allowed = await rate_limiter.check(scope, identifier, limit=limit, window_seconds=60)
    if not allowed:
        raise RateLimitError("Too many attempts. Please wait a moment and try again.")


@router.post(
    "/register",
    response_model=ApiResponse[UserProfile],
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    auth_service: AuthServiceDep,
    rate_limiter: RateLimiterDep,
    settings: SettingsDep,
) -> ApiResponse[UserProfile]:
    await _enforce_rate_limit(
        rate_limiter=rate_limiter,
        scope="auth:register:ip",
        identifier=_client_identifier(request),
        limit=settings.rate_limit_register_per_minute,
    )

    user = await auth_service.register(
        email=payload.email,
        password=payload.password,
        name=payload.name,
    )
    return ok(UserProfile.model_validate(user))


@router.post(
    "/login",
    response_model=ApiResponse[TokenPair],
    summary="Exchange credentials for an access/refresh token pair",
)
async def login(
    payload: LoginRequest,
    request: Request,
    auth_service: AuthServiceDep,
    rate_limiter: RateLimiterDep,
    settings: SettingsDep,
) -> ApiResponse[TokenPair]:
    client_id = _client_identifier(request)
    await _enforce_rate_limit(
        rate_limiter=rate_limiter,
        scope="auth:login:ip",
        identifier=client_id,
        limit=settings.rate_limit_login_per_minute,
    )
    await _enforce_rate_limit(
        rate_limiter=rate_limiter,
        scope="auth:login:email",
        identifier=payload.email.lower(),
        limit=settings.rate_limit_login_per_minute,
    )

    user = await auth_service.authenticate(email=payload.email, password=payload.password)
    return ok(auth_service.issue_token_pair(user.id))


@router.post(
    "/refresh",
    response_model=ApiResponse[AccessToken],
    summary="Exchange a refresh token for a new access token",
)
async def refresh(
    payload: RefreshRequest,
    auth_service: AuthServiceDep,
) -> ApiResponse[AccessToken]:
    token = await auth_service.refresh_access_token(payload.refresh_token)
    return ok(token)


@router.get(
    "/me",
    response_model=ApiResponse[UserProfile],
    summary="Current authenticated user",
)
async def me(current_user: CurrentUserDep) -> ApiResponse[UserProfile]:
    return ok(UserProfile.model_validate(current_user))


@router.post(
    "/logout",
    response_model=ApiResponse[None],
    summary="Revoke the presented access token",
)
async def logout(
    token: BearerTokenRequiredDep,
    auth_service: AuthServiceDep,
) -> ApiResponse[None]:
    await auth_service.logout(token)
    return ok(None)
