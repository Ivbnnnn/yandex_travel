import secrets

from fastapi import HTTPException, Request

from .service import AuthenticateService


class CookieRequestGuard:
    """HTTP protection for cookie authentication; no database access."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, tokens: AuthenticateService, allowed_origins: set[str]):
        self.tokens = tokens
        self.allowed_origins = allowed_origins

    def verify_origin(self, request: Request) -> None:
        if request.headers.get("origin") not in self.allowed_origins:
            raise HTTPException(403, "Invalid origin")

    def verify_csrf(self, request: Request, session_id: str) -> None:
        cookie = request.cookies.get("csrf_token")
        header = request.headers.get("X-CSRF-Token")
        if (
            not cookie
            or not header
            or not cookie.isascii()
            or not header.isascii()
            or not secrets.compare_digest(cookie, header)
            or not self.tokens.verify_csrf_token(header, session_id)
        ):
            raise HTTPException(403, "Invalid CSRF token")
