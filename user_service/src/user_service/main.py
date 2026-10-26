from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from shared.auth import AuthenticateService, InternalJWTService

from shared import Database, create_app

from .api.auth import router as auth_router
from .api.users import router as users_router
from .config import Config, get_config
from .security import PasswordService


def create_user_app(settings: Config | None = None, database: Database | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        current = settings or get_config()
        db = database or Database(current.DATABASE_URL)
        try:
            app.state.settings = current
            app.state.db = db
            app.state.service_name = current.SERVICE_NAME
            app.state.tokens = AuthenticateService(
                private_key=Path(current.AUTH_PRIVATE_KEY_PATH).read_text(encoding="utf-8"),
                public_key=Path(current.AUTH_PUBLIC_KEY_PATH).read_text(encoding="utf-8"),
                csrf_secret=current.CSRF_SECRET,
                access_ttl=timedelta(seconds=current.ACCESS_TTL_SECONDS),
                refresh_ttl=timedelta(seconds=current.REFRESH_TTL_SECONDS),
            )
            app.state.internal_jwt = InternalJWTService(
                public_key=Path(current.GATEWAY_PUBLIC_KEY_PATH).read_text(encoding="utf-8")
            )
            app.state.passwords = PasswordService()
            yield
        finally:
            await db.dispose()

    app = create_app(title="User Service", routers=[auth_router, users_router], lifespan=lifespan)

    @app.get("/health/live", tags=["Health"])
    async def live():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Health"])
    async def ready():
        try:
            await app.state.db.ping()
        except Exception:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return {"status": "ok"}

    return app


app = create_user_app()
