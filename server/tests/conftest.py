"""Shared pytest fixtures.

Tests use an in-memory SQLite (via aiosqlite) so the suite runs without
Docker. The Postgres-only Alembic migration is bypassed: tables are created
from the ORM metadata for the test database. Production still uses the
Alembic migration against Postgres.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from nutriroll.api.app import create_app
from nutriroll.db import models as _models
from nutriroll.db.base import Base
from nutriroll.db.session import get_session

assert _models is not None  # keep import side-effect referenced for pyright


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    sessionmaker = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()
