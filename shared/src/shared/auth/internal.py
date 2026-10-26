import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError


class InternalJWTError(Exception):
    pass


class InternalJWTService:
    """Gateway signs, upstream services verify with the gateway public key."""

    ALGORITHM = "RS256"
    ISSUER = "api-gateway"

    def __init__(
        self,
        public_key: str,
        private_key: str | None = None,
        ttl: timedelta = timedelta(seconds=60),
    ):
        self.public_key = public_key
        self.private_key = private_key
        self.ttl = ttl

    def create_token(self, user_id: str, session_id: str, audience: str) -> str:
        if self.private_key is None:
            raise RuntimeError("Private key is required")
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": user_id,
                "sid": session_id,
                "type": "internal",
                "iss": self.ISSUER,
                "aud": audience,
                "iat": now,
                "nbf": now,
                "exp": now + self.ttl,
                "jti": secrets.token_urlsafe(16),
            },
            self.private_key,
            algorithm=self.ALGORITHM,
        )

    def verify_token(self, token: str, audience: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.ALGORITHM],
                issuer=self.ISSUER,
                audience=audience,
                options={
                    "require": ["sub", "sid", "type", "iss", "aud", "iat", "nbf", "exp", "jti"]
                },
                leeway=5,
            )
            for claim in ("sub", "sid", "jti"):
                if not isinstance(payload[claim], str) or not payload[claim]:
                    raise InternalJWTError(f"Invalid {claim}")
            if payload["type"] != "internal":
                raise InternalJWTError("Invalid token type")
            return payload
        except InvalidTokenError as exc:
            raise InternalJWTError("Invalid or expired internal token") from exc
