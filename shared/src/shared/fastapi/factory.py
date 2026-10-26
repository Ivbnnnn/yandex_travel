from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import APIRouter, FastAPI
from shared.errors import (
    ApplicationError,
    application_error_handler,
    unexpected_error_handler,
)
from starlette.middleware import Middleware
from starlette.routing import BaseRoute
from starlette.types import ExceptionHandler, Lifespan


def create_app(
    title: str,
    version: str = "1.0.0",
    *,
    description: str | None = None,
    lifespan: Lifespan[FastAPI] | None = None,
    routers: Sequence[APIRouter] = (),
    routes: Sequence[BaseRoute] = (),
    middleware: Sequence[Middleware] = (),
    exception_handlers: Mapping[int | type[Exception], ExceptionHandler] | None = None,
    dependencies: Sequence[Any] = (),
    openapi_url: str | None = "/openapi.json",
    docs_url: str | None = "/docs",
    redoc_url: str | None = "/redoc",
    debug: bool = False,
    **kwargs: Any,
) -> FastAPI:
    handlers = {
        ApplicationError: application_error_handler,
        Exception: unexpected_error_handler,
        **(exception_handlers or {}),
    }
    app = FastAPI(
        title=title,
        version=version,
        description=description,
        lifespan=lifespan,
        routes=list(routes),
        middleware=list(middleware),
        exception_handlers=handlers,
        dependencies=list(dependencies),
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
        debug=debug,
        **kwargs,
    )
    for router in routers:
        app.include_router(router)
    return app
