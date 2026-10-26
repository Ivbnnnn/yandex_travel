from dataclasses import dataclass

from fastapi import HTTPException, Request

from .internal import InternalJWTError


@dataclass(frozen=True)
class InternalPrincipal:
    user_id: str
    session_id: str


async def get_internal_principal(request: Request) -> InternalPrincipal:
    """Verify once per request through FastAPI's dependency cache.

    The app lifespan supplies state.internal_jwt and state.service_name.
    """
    token = request.headers.get("X-Internal-Token")
    if not token:
        raise HTTPException(401, "Missing internal token")
    try:
        claims = request.app.state.internal_jwt.verify_token(
            token, audience=request.app.state.service_name
        )
    except InternalJWTError as exc:
        raise HTTPException(401, "Invalid internal token") from exc
    return InternalPrincipal(user_id=claims["sub"], session_id=claims["sid"])
