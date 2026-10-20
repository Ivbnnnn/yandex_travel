from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager

from fastapi import FastAPI

Lifespan = Callable[
    [FastAPI],
    AbstractAsyncContextManager[None]
]


def create_app(
    title: str,
    version: str = "1.0.0",
    lifespan: Lifespan | None = None,
) -> FastAPI:
    app = FastAPI(
        title=title,
        version=version,
        lifespan=lifespan,
    )

    # Общие middleware
    # Общие exception handlers
    # Общая конфигурация

    return app