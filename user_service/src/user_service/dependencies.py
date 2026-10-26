from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from shared.auth import (
    AuthenticateService,
    AuthenticationError,
    CookieRequestGuard,
    InternalPrincipal,
    get_internal_principal,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Config
from .exceptions import InvalidRefreshTokenError
from .repositories import SessionRepository, UserRepository
from .security import PasswordService, RefreshCredentials
from .services.auth import AuthService
from .services.users import UserService


def get_settings(request: Request) -> Config:
    return request.app.state.settings


def get_authenticate_service(request: Request) -> AuthenticateService:
    return request.app.state.tokens


def get_password_service(request: Request) -> PasswordService:
    return request.app.state.passwords


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with aclosing(request.app.state.db.get_session()) as sessions:
        async for session in sessions:
            yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
TokensDep = Annotated[AuthenticateService, Depends(get_authenticate_service)]
SettingsDep = Annotated[Config, Depends(get_settings)]
PasswordsDep = Annotated[PasswordService, Depends(get_password_service)]


def get_user_service(session: SessionDep, passwords: PasswordsDep) -> UserService:
    return UserService(UserRepository(session), passwords)


def get_auth_service(
    session: SessionDep, tokens: TokensDep, passwords: PasswordsDep
) -> AuthService:
    return AuthService(UserRepository(session), SessionRepository(session), tokens, passwords)


def get_current_user(
    principal: Annotated[InternalPrincipal, Depends(get_internal_principal)],
) -> int:
    try:
        user_id = int(principal.user_id)
        if user_id <= 0:
            raise ValueError
        return user_id
    except ValueError as exc:
        raise HTTPException(401, "Invalid user ID") from exc


def require_auth_origin(request: Request, settings: SettingsDep, tokens: TokensDep) -> None:
    CookieRequestGuard(tokens, set(settings.ALLOWED_ORIGINS)).verify_origin(request)


def get_refresh_credentials(
    request: Request, settings: SettingsDep, tokens: TokensDep
) -> RefreshCredentials:
    guard = CookieRequestGuard(tokens, set(settings.ALLOWED_ORIGINS))
    guard.verify_origin(request)
    token = request.cookies.get("refresh_token")
    if not token:
        raise InvalidRefreshTokenError()
    try:
        claims = tokens.verify_refresh_token(token)
        user_id = int(claims["sub"])
        if user_id <= 0:
            raise ValueError
        session_id = UUID(claims["sid"])
    except (AuthenticationError, ValueError) as exc:
        raise InvalidRefreshTokenError() from exc
    guard.verify_csrf(request, claims["sid"])
    return RefreshCredentials(token=token, user_id=user_id, session_id=session_id)
