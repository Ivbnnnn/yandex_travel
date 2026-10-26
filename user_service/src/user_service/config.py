from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from shared.config import BaseConfig


class Config(BaseConfig):
    DATABASE_URL: str
    AUTH_PRIVATE_KEY_PATH: str
    AUTH_PUBLIC_KEY_PATH: str
    GATEWAY_PUBLIC_KEY_PATH: str
    CSRF_SECRET: str = Field(min_length=32)
    SERVICE_NAME: str = "user-service"
    ACCESS_TTL_SECONDS: int = Field(default=900, gt=0)
    REFRESH_TTL_SECONDS: int = Field(default=2592000, gt=0)
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8000"]

    @model_validator(mode="after")
    def validate_cookies(self) -> "Config":
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("SameSite=None requires secure cookies")
        return self


@lru_cache
def get_config() -> Config:
    return Config()
