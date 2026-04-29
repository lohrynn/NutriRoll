"""Tests for /v1/me/profile."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_profile_default_get_creates_singleton(client: AsyncClient) -> None:
    r = await client.get("/v1/me/profile")
    assert r.status_code == 200
    data = r.json()
    assert data == {
        "dietary_mode": "",
        "allergens": [],
        "default_time_budget_min": None,
        "goal": "",
        "locale": "en",
        "onboarded": False,
    }
    # Idempotent: same shape on a second GET.
    r2 = await client.get("/v1/me/profile")
    assert r2.json() == data


@pytest.mark.asyncio
async def test_profile_put_round_trip(client: AsyncClient) -> None:
    body: dict[str, Any] = {
        "dietary_mode": "vegan",
        "allergens": ["dairy", "nuts"],
        "default_time_budget_min": 25,
        "goal": "more protein",
        "locale": "de",
        "onboarded": True,
    }
    r = await client.put("/v1/me/profile", json=body)
    assert r.status_code == 200
    assert r.json() == body

    r = await client.get("/v1/me/profile")
    assert r.json() == body


@pytest.mark.asyncio
async def test_profile_rejects_unknown_dietary_mode(client: AsyncClient) -> None:
    r = await client.put(
        "/v1/me/profile",
        json={
            "dietary_mode": "carnivore",
            "allergens": [],
            "default_time_budget_min": None,
            "goal": "",
            "locale": "en",
            "onboarded": True,
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_profile_rejects_non_positive_time_budget(client: AsyncClient) -> None:
    r = await client.put(
        "/v1/me/profile",
        json={
            "dietary_mode": "",
            "allergens": [],
            "default_time_budget_min": 0,
            "goal": "",
            "locale": "en",
            "onboarded": False,
        },
    )
    assert r.status_code == 422
