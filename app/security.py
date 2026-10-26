import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import Response
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool

from .config import Settings
from .errors import AuthenticationError


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class TokenService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create(self, user_id: UUID, session_id: UUID, kind: str, ttl: int) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "type": kind,
                "jti": secrets.token_urlsafe(24),
                "iat": now,
                "nbf": now,
                "exp": now + timedelta(seconds=ttl),
                "iss": "travel-monolith",
                "aud": "travel-api",
            },
            self.settings.JWT_SECRET,
            algorithm="HS256",
        )

    def verify(self, value: str, kind: str) -> dict:
        try:
            claims = jwt.decode(
                value,
                self.settings.JWT_SECRET,
                algorithms=["HS256"],
                issuer="travel-monolith",
                audience="travel-api",
                options={"require": ["sub", "sid", "type", "jti", "exp", "iat", "nbf"]},
            )
            if claims["type"] != kind:
                raise ValueError
            claims["user_id"] = UUID(claims["sub"])
            claims["session_id"] = UUID(claims["sid"])
            return claims
        except (InvalidTokenError, ValueError, TypeError, AttributeError) as exc:
            raise AuthenticationError("Invalid or expired token") from exc

    def csrf(self, sid: UUID) -> str:
        nonce = secrets.token_hex(32)
        digest = hmac.new(
            self.settings.CSRF_SECRET.encode(), f"{sid}:{nonce}".encode(), hashlib.sha256
        ).hexdigest()
        return f"{nonce}.{digest}"

    def valid_csrf(self, value: str, sid: UUID) -> bool:
        try:
            nonce, signature = value.split(".")
            if len(nonce) != 64 or len(signature) != 64:
                return False
            bytes.fromhex(nonce)
            bytes.fromhex(signature)
            expected = hmac.new(
                self.settings.CSRF_SECRET.encode(), f"{sid}:{nonce}".encode(), hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except (ValueError, TypeError):
            return False

    def pair(self, user_id: UUID, sid: UUID) -> dict[str, str]:
        return {
            "access_token": self.create(user_id, sid, "access", self.settings.ACCESS_TTL_SECONDS),
            "refresh_token": self.create(
                user_id, sid, "refresh", self.settings.REFRESH_TTL_SECONDS
            ),
            "csrf_token": self.csrf(sid),
        }

    def set_cookies(self, response: Response, pair: dict[str, str]):
        for name in ("access_token", "refresh_token", "csrf_token"):
            ttl = (
                self.settings.ACCESS_TTL_SECONDS
                if name == "access_token"
                else self.settings.REFRESH_TTL_SECONDS
            )
            response.set_cookie(
                name,
                pair[name],
                max_age=ttl,
                httponly=name != "csrf_token",
                secure=self.settings.COOKIE_SECURE,
                samesite="lax",
                path="/",
            )
        response.headers["Cache-Control"] = "no-store"

    def clear_cookies(self, response: Response):
        for name in ("access_token", "refresh_token", "csrf_token"):
            response.delete_cookie(
                name,
                path="/",
                httponly=name != "csrf_token",
                secure=self.settings.COOKIE_SECURE,
                samesite="lax",
            )


class PasswordService:
    def __init__(self):
        self.hasher = PasswordHash.recommended()
        self.dummy = self.hasher.hash("dummy-login-password")

    async def hash(self, password: str) -> str:
        return await run_in_threadpool(self.hasher.hash, password)

    async def verify(self, password: str, stored: str | None) -> bool:
        valid = await run_in_threadpool(self.hasher.verify, password, stored or self.dummy)
        return bool(stored) and valid
