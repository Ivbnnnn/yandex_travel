from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ..cookies import clear_auth_cookies
from ..dependencies import SettingsDep, get_current_user, get_user_service
from ..schemas import UserRead, UserUpdate
from ..services.users import UserService

router = APIRouter(prefix="/users", tags=["Users"])
CurrentUser = Annotated[int, Depends(get_current_user)]
UsersDep = Annotated[UserService, Depends(get_user_service)]


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUser, service: UsersDep, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return await service.profile(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(data: UserUpdate, current_user: CurrentUser, service: UsersDep):
    return await service.update(current_user, data)


@router.delete("/me", status_code=204)
async def delete_me(
    current_user: CurrentUser, service: UsersDep, response: Response, settings: SettingsDep
):
    await service.delete(current_user)
    clear_auth_cookies(response, settings)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, current_user: CurrentUser, service: UsersDep):
    if user_id != current_user:
        raise HTTPException(403, "Access denied")
    return await service.profile(user_id)
