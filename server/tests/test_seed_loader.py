"""Tests for the seed loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from nutriroll.db import models as _models
from nutriroll.db.base import Base
from nutriroll.domain.component import Category, CookingMethod
from nutriroll.tools import seed as seed_module

assert _models is not None  # keep import side-effect referenced for pyright

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = REPO_ROOT / "data" / "seed"


@pytest_asyncio.fixture
async def patch_sessionmaker(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(seed_module, "get_sessionmaker", lambda: sessionmaker)
    yield sessionmaker
    await engine.dispose()


def test_read_seed_parses_all_csv_rows() -> None:
    components = seed_module.read_seed(
        SEED_DIR / "components.csv", SEED_DIR / "cooking_methods.csv"
    )
    assert len(components) >= 60
    categories = {c.category for c in components}
    assert categories == {
        Category.BASE,
        Category.VEGETABLE,
        Category.SAUCE,
        Category.TOPPING,
    }
    # Every component has at least one cooking method and a default that is
    # in its method list (this is enforced by the Component invariant; if
    # parsing returns components, the invariant already held).
    for c in components:
        assert c.cooking_methods
        assert c.default_cooking_method in {s.method for s in c.cooking_methods}


def test_read_seed_maps_legacy_saute_alias_to_pan_fry() -> None:
    components = seed_module.read_seed(
        SEED_DIR / "components.csv", SEED_DIR / "cooking_methods.csv"
    )
    spinach = next(c for c in components if c.name == "Spinach")
    methods = {s.method for s in spinach.cooking_methods}
    assert CookingMethod.PAN_FRY in methods


async def test_upsert_inserts_into_empty_db(patch_sessionmaker: None) -> None:
    components = seed_module.read_seed(
        SEED_DIR / "components.csv", SEED_DIR / "cooking_methods.csv"
    )
    inserted, skipped = await seed_module.upsert_components(components, force=False)
    assert inserted == len(components)
    assert skipped == 0


async def test_upsert_refuses_non_empty_db_without_force(patch_sessionmaker: None) -> None:
    components = seed_module.read_seed(
        SEED_DIR / "components.csv", SEED_DIR / "cooking_methods.csv"
    )
    await seed_module.upsert_components(components, force=False)
    with pytest.raises(RuntimeError, match="--force"):
        await seed_module.upsert_components(components, force=False)


async def test_upsert_is_idempotent_with_force(patch_sessionmaker: None) -> None:
    components = seed_module.read_seed(
        SEED_DIR / "components.csv", SEED_DIR / "cooking_methods.csv"
    )
    first_inserted, _ = await seed_module.upsert_components(components, force=False)
    second_inserted, second_skipped = await seed_module.upsert_components(components, force=True)
    assert second_inserted == 0
    assert second_skipped == first_inserted
