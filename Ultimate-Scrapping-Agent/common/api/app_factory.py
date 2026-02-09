"""FastAPI application factory with database lifespan."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from common.persistence.database import close_db, init_db


def create_app(
    title: str = "Claude Agent",
    db_url: str = "sqlite+aiosqlite:///data/scraper.db",
    routers: list[Any] | None = None,
) -> FastAPI:
    """Create a FastAPI application with DB lifespan management.

    Args:
        title: Application title.
        db_url: Async database URL.
        routers: List of APIRouter instances to include.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        await init_db(db_url)
        yield
        await close_db()

    app = FastAPI(title=title, lifespan=lifespan)

    if routers:
        for router in routers:
            app.include_router(router)

    return app
