from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.monolith", extra="ignore")
    DATABASE_URL: str
    JWT_SECRET: str = Field(min_length=32)
    CSRF_SECRET: str = Field(min_length=32)
    ACCESS_TTL_SECONDS: int = Field(default=900, gt=0)
    REFRESH_TTL_SECONDS: int = Field(default=2592000, gt=0)
    HOLD_TTL_SECONDS: int = Field(default=900, gt=0)
    COOKIE_SECURE: bool = True
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    TIMEZONE: str = "Europe/Moscow"
    SEED_DATA: bool = True
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = Field(min_length=12)
    DEMO_PAYMENTS: bool = True

    @model_validator(mode="after")
    def valid_timezone(self):
        from zoneinfo import ZoneInfo

        ZoneInfo(self.TIMEZONE)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
