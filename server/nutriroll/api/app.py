"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nutriroll.api.routers import (
    components,
    healthz,
    history,
    pantry,
    ratings,
    recipe,
    roll,
    shopping,
    stores,
)
from nutriroll.config import get_settings
from nutriroll.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("nutriroll.api")
    log.info("startup", env=settings.env)
    try:
        yield
    finally:
        log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="NutriRoll API",
        version="0.0.0",
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url="/docs" if settings.env != "prod" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(healthz.router)
    app.include_router(components.router)
    app.include_router(roll.router)
    app.include_router(recipe.router)
    app.include_router(pantry.router)
    app.include_router(stores.router)
    app.include_router(shopping.router)
    app.include_router(ratings.router)
    app.include_router(history.router)

    return app


app = create_app()
