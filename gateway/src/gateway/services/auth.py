from fastapi import HTTPException, Request
from shared.auth import (
    AuthenticateService,
    AuthenticationError,
    CookieRequestGuard,
    InternalJWTService,
)

from gateway.config import FORWARD_COOKIE_ROUTES, PUBLIC_ROUTES, ServiceConfig


class GatewayAuthService:
    BLOCKED_HEADERS = {
        "authorization",
        "cookie",
        "x-user-id",
        "x-user-role",
        "x-internal-token",
        "trust-token",
        "forwarded",
        "x-forwarded-for",
        "x-forwarded-host",
        "x-forwarded-proto",
        "host",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-length",
        "accept-encoding",
    }

    def __init__(
        self,
        auth_service: AuthenticateService,
        internal_jwt: InternalJWTService,
        allowed_origins: set[str],
    ):
        self.auth_service = auth_service
        self.internal_jwt = internal_jwt
        self.guard = CookieRequestGuard(auth_service, allowed_origins)

    def authenticate(self, request: Request) -> dict:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(401, "Not authenticated")
        try:
            return self.auth_service.verify_access_token(token)
        except AuthenticationError as exc:
            raise HTTPException(401, "Invalid access token") from exc

    def create_headers(
        self, request: Request, service: str, path: str, config: ServiceConfig
    ) -> dict[str, str]:
        route = (service, path.strip("/"), request.method)
        blocked = self.BLOCKED_HEADERS | {
            item.strip().lower()
            for item in request.headers.get("connection", "").split(",")
            if item.strip()
        }
        headers = {
            key: value for key, value in request.headers.items() if key.lower() not in blocked
        }
        headers["Accept-Encoding"] = "identity"

        if request.method not in self.guard.SAFE_METHODS:
            self.guard.verify_origin(request)

        if route not in PUBLIC_ROUTES:
            claims = self.authenticate(request)
            if request.method not in self.guard.SAFE_METHODS:
                self.guard.verify_csrf(request, claims["sid"])
            headers["X-Internal-Token"] = self.internal_jwt.create_token(
                user_id=claims["sub"],
                session_id=claims["sid"],
                audience=config.audience,
            )

        # Refresh/logout authenticate with refresh JWT in user_service.
        # They must work even when the access JWT has expired.
        if route in FORWARD_COOKIE_ROUTES:
            cookie = request.headers.get("cookie")
            if cookie:
                headers["Cookie"] = cookie
        return headers
