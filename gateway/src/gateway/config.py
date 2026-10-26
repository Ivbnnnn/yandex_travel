from dataclasses import dataclass
from functools import lru_cache

from pydantic import Field
from shared.config import BaseConfig


@dataclass(frozen=True)
class ServiceConfig:
    url: str
    audience: str


class Config(BaseConfig):
    AUTH_PUBLIC_KEY_PATH: str
    GATEWAY_PRIVATE_KEY_PATH: str
    GATEWAY_PUBLIC_KEY_PATH: str
    CSRF_SECRET: str = Field(min_length=32)
    GATEWAY_USER_SERVICE_URL: str = "http://localhost:8001"
    GATEWAY_DOCUMENT_SERVICE_URL: str = "http://localhost:8002"
    GATEWAY_AI_SERVICE_URL: str = "http://localhost:8003"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8000"]

    def services(self) -> dict[str, ServiceConfig]:
        return {
            "users": ServiceConfig(self.GATEWAY_USER_SERVICE_URL, "user-service"),
            "documents": ServiceConfig(self.GATEWAY_DOCUMENT_SERVICE_URL, "document-service"),
            "ai": ServiceConfig(self.GATEWAY_AI_SERVICE_URL, "ai-service"),
        }


@lru_cache
def get_config() -> Config:
    return Config()


PUBLIC_ROUTES = {
    ("users", "auth/register", "POST"),
    ("users", "auth/login", "POST"),
    ("users", "auth/refresh", "POST"),
    ("users", "auth/logout", "POST"),
}
# Responses allowed to set/delete browser cookies.
COOKIE_ROUTES = PUBLIC_ROUTES | {("users", "users/me", "DELETE")}
# Ordinary services never receive the browser's JWT cookies.
FORWARD_COOKIE_ROUTES = {
    ("users", "auth/refresh", "POST"),
    ("users", "auth/logout", "POST"),
}
