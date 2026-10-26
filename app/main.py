import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from functools import partial

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .api import router
from .config import get_settings
from .database import Database
from .errors import (
    BusinessError,
    business_error_handler,
    integrity_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from .middleware import AuthenticationMiddleware
from .security import PasswordService, TokenService
from .seed import seed_data
from .services.notifications import NotificationService
from .uow import UnitOfWork


async def housekeeping(app):
    service = NotificationService(app.state.uow_factory, app.state.settings)
    while True:
        try:
            await service.maintenance()
        except Exception:
            logging.getLogger(__name__).exception("Notification/expiry job failed")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app):
    settings = get_settings()
    database = Database(settings.DATABASE_URL)
    app.state.settings = settings
    app.state.tokens = TokenService(settings)
    app.state.passwords = PasswordService()
    app.state.uow_factory = partial(UnitOfWork, database.sessions)
    app.state.database = database
    worker = None
    try:
        await database.create_schema()
        await seed_data(app.state.uow_factory, settings, app.state.passwords)
        worker = asyncio.create_task(housekeeping(app))
        yield
    finally:
        if worker:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker
        await database.close()


app = FastAPI(
    title="Travel MVP — monolith",
    lifespan=lifespan,
    exception_handlers={
        BusinessError: business_error_handler,
        IntegrityError: integrity_error_handler,
        RequestValidationError: validation_error_handler,
        Exception: unexpected_error_handler,
    },
)
app.add_middleware(AuthenticationMiddleware)
app.include_router(router)


@app.get("/", include_in_schema=False)
async def index():
    return {"service": "travel-mvp", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["Health"])
async def health():
    try:
        await app.state.database.ping()
    except Exception:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok"}
