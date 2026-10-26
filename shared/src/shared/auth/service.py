import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from jwt import InvalidTokenError


class AuthenticationError(Exception):
    pass


class AuthenticateService:
    def __init__(
        self,
        private_key: str | None,
        public_key: str,
        csrf_secret: str,
        issuer: str = "auth-service",
        audience: str = "api",
        access_ttl: timedelta = timedelta(minutes=15),
        refresh_ttl: timedelta = timedelta(days=30),
    ):
        self.private_key = private_key
        self.public_key = public_key
        self.csrf_secret = csrf_secret.encode()
        self.issuer = issuer
        self.audience = audience
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl

    def _create_token(
        self,
        user_id: str,
        session_id: str,
        token_type: Literal["access", "refresh"],
        ttl: timedelta,
    ) -> str:
        if not self.private_key:
            raise RuntimeError("Private key is required")

        now = datetime.now(timezone.utc)

        payload = {
            "sub": user_id,
            "sid": session_id,
            "type": token_type,
            "jti": secrets.token_urlsafe(32),
            "iat": now,
            "nbf": now,
            "exp": now + ttl,
            "iss": self.issuer,
            "aud": self.audience,
        }

        return jwt.encode(
            payload,
            self.private_key,
            algorithm="RS256",
        )

    def create_access_token(
        self,
        user_id: str,
        session_id: str,
    ) -> str:
        return self._create_token(
            user_id,
            session_id,
            "access",
            self.access_ttl,
        )

    def create_refresh_token(
        self,
        user_id: str,
        session_id: str,
    ) -> str:
        return self._create_token(
            user_id,
            session_id,
            "refresh",
            self.refresh_ttl,
        )

    def verify_token(
        self,
        token: str,
        token_type: Literal["access", "refresh"],
    ) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "require": [
                        "sub",
                        "sid",
                        "type",
                        "jti",
                        "iat",
                        "nbf",
                        "exp",
                        "iss",
                        "aud",
                    ]
                },
            )

            if payload.get("type") != token_type:
                raise AuthenticationError("Invalid token type")

            if not isinstance(payload.get("sub"), str) or not payload["sub"]:
                raise AuthenticationError("Invalid user ID")

            if not isinstance(payload.get("sid"), str) or not payload["sid"]:
                raise AuthenticationError("Invalid session ID")

            if not isinstance(payload.get("jti"), str) or not payload["jti"]:
                raise AuthenticationError("Invalid token ID")

            return payload

        except InvalidTokenError as exc:
            raise AuthenticationError("Invalid or expired token") from exc

    def verify_access_token(
        self,
        token: str,
    ) -> dict[str, Any]:
        return self.verify_token(token, "access")

    def verify_refresh_token(
        self,
        token: str,
    ) -> dict[str, Any]:
        return self.verify_token(token, "refresh")

    def create_csrf_token(self, session_id: str) -> str:
        nonce = secrets.token_hex(32)
        message = f"{len(session_id)}!{session_id}!{nonce}"

        signature = hmac.new(
            self.csrf_secret,
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        return f"{nonce}.{signature}"

    def verify_csrf_token(
        self,
        token: str,
        session_id: str,
    ) -> bool:
        try:
            nonce, signature = token.split(".")

            if len(nonce) != 64 or len(signature) != 64:
                return False

            bytes.fromhex(nonce)
            bytes.fromhex(signature)

        except (ValueError, AttributeError):
            return False

        message = f"{len(session_id)}!{session_id}!{nonce}"

        expected = hmac.new(
            self.csrf_secret,
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def create_token_pair(
        self,
        user_id: str,
        session_id: str,
    ) -> dict[str, str]:
        return {
            "access_token": self.create_access_token(user_id, session_id),
            "refresh_token": self.create_refresh_token(user_id, session_id),
            "csrf_token": self.create_csrf_token(session_id),
        }
