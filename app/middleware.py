import re
import secrets
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware

from .errors import AuthenticationError, BusinessError, ForbiddenError, error_response

ID = r"[0-9a-fA-F-]{36}"
PUBLIC_GET = re.compile(
    rf"^/api/v1/(filters|hotels|hotels/search|hotels/compare|hotels/{ID}|hotels/{ID}/rooms|"
    rf"rooms/{ID}|rooms/{ID}/rates)$"
)
SAFE = {"GET", "HEAD", "OPTIONS"}
AUTH = "/api/v1/auth/"


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authenticate at the HTTP boundary. Services receive a verified UUID."""

    async def dispatch(self, request, call_next):
        request.state.user_id = None
        request.state.session_id = None
        request.state.user_role = None
        path, method = request.url.path.rstrip("/"), request.method
        if not path.startswith("/api/"):
            return await call_next(request)
        public = method == "GET" and bool(PUBLIC_GET.fullmatch(path))
        public_write = method == "POST" and path in {
            AUTH + "register",
            AUTH + "login",
            "/api/v1/analytics/events",
        }
        refresh = method == "POST" and path in {AUTH + "refresh", AUTH + "logout"}
        tokens, settings = request.app.state.tokens, request.app.state.settings
        try:
            bearer = request.headers.get("authorization")
            if refresh:
                raw = request.cookies.get("refresh_token")
                if not raw:
                    raise AuthenticationError("Missing refresh token")
                claims = tokens.verify(raw, "refresh")
                self.check_origin(request, settings)
                self.check_csrf(request, tokens, claims["session_id"])
                request.state.user_id = claims["user_id"]
                request.state.session_id = claims["session_id"]
                request.state.refresh_token = raw
            else:
                raw = request.cookies.get("access_token")
                if bearer:
                    scheme, _, raw = bearer.partition(" ")
                    if scheme.lower() != "bearer" or not raw:
                        raise AuthenticationError("Invalid Authorization header")
                try:
                    if not raw:
                        raise AuthenticationError()
                    claims = tokens.verify(raw, "access")
                    async with request.app.state.uow_factory() as uow:
                        user = await uow.users.get(claims["user_id"])
                        session = await uow.sessions_repo.get(claims["session_id"])
                        if (
                            not user
                            or not user.is_active
                            or not session
                            or session.user_id != user.id
                            or session.revoked_at
                            or session.expires_at <= datetime.now(UTC)
                        ):
                            raise AuthenticationError("Session revoked")
                        request.state.user_id = user.id
                        request.state.user_role = user.role
                        request.state.session_id = session.id
                except AuthenticationError:
                    if not public and not public_write:
                        raise
                if public_write:
                    self.check_origin(request, settings)
                elif method not in SAFE and not bearer:
                    self.check_origin(request, settings)
                    self.check_csrf(request, tokens, request.state.session_id)
            response = await call_next(request)
            if not public or path.startswith(AUTH):
                response.headers["Cache-Control"] = "no-store"
            return response
        except BusinessError as exc:
            return error_response(exc)

    @staticmethod
    def check_origin(request, settings):
        if request.headers.get("origin") not in settings.ALLOWED_ORIGINS:
            raise ForbiddenError("Origin is not allowed")

    @staticmethod
    def check_csrf(request, tokens, sid):
        cookie = request.cookies.get("csrf_token", "")
        header = request.headers.get("x-csrf-token", "")
        if (
            not cookie
            or not header
            or not cookie.isascii()
            or not header.isascii()
            or not secrets.compare_digest(cookie, header)
            or not tokens.valid_csrf(header, sid)
        ):
            raise ForbiddenError("Invalid CSRF token")
