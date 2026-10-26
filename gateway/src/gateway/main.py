from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.auth import AuthenticateService, InternalJWTService

from gateway.config import Config, get_config
from gateway.routes.proxy import router
from gateway.services.auth import GatewayAuthService
from gateway.services.proxy import GatewayProxyService
from shared import create_app


def create_gateway_app(
    settings: Config | None = None, upstream_client: httpx.AsyncClient | None = None
) -> FastAPI:
    current = settings or get_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with AsyncExitStack() as stack:
            client = upstream_client
            if client is None:
                client = await stack.enter_async_context(
                    httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False)
                )
            app.state.services = current.services()
            app.state.auth = GatewayAuthService(
                auth_service=AuthenticateService(
                    private_key=None,
                    public_key=Path(current.AUTH_PUBLIC_KEY_PATH).read_text(encoding="utf-8"),
                    csrf_secret=current.CSRF_SECRET,
                ),
                internal_jwt=InternalJWTService(
                    private_key=Path(current.GATEWAY_PRIVATE_KEY_PATH).read_text(encoding="utf-8"),
                    public_key=Path(current.GATEWAY_PUBLIC_KEY_PATH).read_text(encoding="utf-8"),
                ),
                allowed_origins=set(current.ALLOWED_ORIGINS),
            )
            app.state.proxy = GatewayProxyService(client)
            yield

    app = create_app(title="API Gateway", routers=[router], lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=current.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @app.get("/health/live", tags=["Health"])
    async def live():
        return {"status": "ok"}

    return app
