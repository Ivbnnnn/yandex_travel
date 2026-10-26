from typing import Annotated

from fastapi import APIRouter, Depends, Response

from ..cookies import clear_auth_cookies, set_auth_cookies
from ..dependencies import (
    SettingsDep,
    TokensDep,
    get_auth_service,
    get_refresh_credentials,
    get_user_service,
    require_auth_origin,
)
from ..schemas import UserCreateRoute, UserLogin, UserRead
from ..security import RefreshCredentials
from ..services.auth import AuthService
from ..services.users import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])
AuthDep = Annotated[AuthService, Depends(get_auth_service)]
UsersDep = Annotated[UserService, Depends(get_user_service)]
RefreshDep = Annotated[RefreshCredentials, Depends(get_refresh_credentials)]


@router.post(
    "/register",
    response_model=UserRead,
    status_code=201,
    dependencies=[Depends(require_auth_origin)],
)
async def register(data: UserCreateRoute, service: UsersDep, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return await service.register(data)


@router.post("/login", response_model=UserRead, dependencies=[Depends(require_auth_origin)])
async def login(
    data: UserLogin,
    response: Response,
    service: AuthDep,
    settings: SettingsDep,
    tokens: TokensDep,
):
    result = await service.login(data)
    set_auth_cookies(response, result.tokens, settings, tokens)
    return result.user


@router.post("/refresh")
async def refresh(
    credentials: RefreshDep,
    response: Response,
    service: AuthDep,
    settings: SettingsDep,
    tokens: TokensDep,
):
    new_tokens = await service.refresh(credentials)
    set_auth_cookies(response, new_tokens, settings, tokens)
    return {"detail": "Session refreshed"}


@router.post("/logout", status_code=204)
async def logout(
    credentials: RefreshDep,
    response: Response,
    service: AuthDep,
    settings: SettingsDep,
):
    await service.logout(credentials)
    clear_auth_cookies(response, settings)
