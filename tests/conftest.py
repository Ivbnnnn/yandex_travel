import os

import httpx
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from gateway.config import Config as GatewayConfig
from gateway.main import create_gateway_app
from shared.database import Database
from shared.db.base import Base
from sqlalchemy import event
from sqlalchemy.engine import make_url
from user_service.config import Config
from user_service.main import create_user_app


@pytest.fixture(scope="session")
def key_paths(tmp_path_factory):
    directory = tmp_path_factory.mktemp("keys")
    paths = {}
    for name in ("auth", "gateway"):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private = directory / f"{name}-private.pem"
        public = directory / f"{name}-public.pem"
        private.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        public.write_bytes(
            key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        paths[f"{name}_private"] = str(private)
        paths[f"{name}_public"] = str(public)
    return paths


@pytest_asyncio.fixture
async def stack(tmp_path, key_paths):
    url = os.environ.get("TEST_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    if not url.startswith("sqlite"):
        assert (make_url(url).database or "").startswith("user_service_test"), (
            "Only a dedicated user_service_test* database may be reset"
        )
    db = Database(url)
    if url.startswith("sqlite"):

        @event.listens_for(db.engine.sync_engine, "connect")
        def enable_fk(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    async with db.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    common = {
        "_env_file": None,
        "AUTH_PUBLIC_KEY_PATH": key_paths["auth_public"],
        "GATEWAY_PUBLIC_KEY_PATH": key_paths["gateway_public"],
        "CSRF_SECRET": "test-csrf-secret-with-at-least-32-chars",
        "ALLOWED_ORIGINS": ["http://localhost:5173"],
    }
    settings = Config(
        **common,
        DATABASE_URL=url,
        AUTH_PRIVATE_KEY_PATH=key_paths["auth_private"],
        COOKIE_SECURE=False,
    )
    user_app = create_user_app(settings, db)
    received = []

    @user_app.middleware("http")
    async def capture(request, call_next):
        received.append({"path": request.url.path, "headers": dict(request.headers)})
        return await call_next(request)

    async with user_app.router.lifespan_context(user_app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=user_app), base_url="http://user-service"
        ) as upstream:
            gateway_settings = GatewayConfig(
                **common,
                GATEWAY_PRIVATE_KEY_PATH=key_paths["gateway_private"],
                GATEWAY_USER_SERVICE_URL="http://user-service",
            )
            gateway_app = create_gateway_app(gateway_settings, upstream)
            async with gateway_app.router.lifespan_context(gateway_app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=gateway_app),
                    base_url="http://testserver",
                    headers={"Origin": "http://localhost:5173"},
                ) as client:
                    yield client, user_app, gateway_app, received
