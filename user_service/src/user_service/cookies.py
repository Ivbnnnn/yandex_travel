from fastapi import Response
from shared.auth import AuthenticateService

from .config import Config


def set_auth_cookies(
    response: Response, tokens: dict[str, str], settings: Config, auth: AuthenticateService
) -> None:
    for name, max_age, http_only in (
        ("access_token", int(auth.access_ttl.total_seconds()), True),
        ("refresh_token", int(auth.refresh_ttl.total_seconds()), True),
        ("csrf_token", int(auth.refresh_ttl.total_seconds()), False),
    ):
        response.set_cookie(
            key=name,
            value=tokens[name],
            max_age=max_age,
            httponly=http_only,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/",
        )
    response.headers["Cache-Control"] = "no-store"


def clear_auth_cookies(response: Response, settings: Config) -> None:
    for name in ("access_token", "refresh_token", "csrf_token"):
        response.delete_cookie(
            name,
            path="/",
            secure=settings.COOKIE_SECURE,
            httponly=name != "csrf_token",
            samesite=settings.COOKIE_SAMESITE,
        )
    response.headers["Cache-Control"] = "no-store"
