"""Tests for /v1/me/profile."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from nutriroll.api.routers import profile as profile_router
from nutriroll.domain.llm_config import LLMKeyValidationError


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
        "roll_weights": {},
        "default_macro_targets": {},
        "equipment": [],
        "llm_weekly_recap_enabled": False,
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
        "roll_weights": {"freshness_boost": 0.8, "variety": 0.6},
        "default_macro_targets": {
            "protein_g": {"value": 50.0, "mode": "min"},
            "fat_g": {"value": 30.0, "mode": "max"},
        },
        "equipment": ["oven", "stovetop", "air_fryer"],
        "llm_weekly_recap_enabled": True,
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


@pytest.mark.asyncio
async def test_profile_llm_default_get_returns_disabled_config(client: AsyncClient) -> None:
    response = await client.get("/v1/me/profile/llm")
    assert response.status_code == 200
    assert response.json() == {
        "enabled_features": [],
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key_set": False,
    }


@pytest.mark.asyncio
async def test_profile_llm_put_round_trip_persists(client: AsyncClient) -> None:
    response = await client.put(
        "/v1/me/profile/llm",
        json={
            "enabled_features": ["component_creation", "weekly_recaps"],
            "provider": "openai",
            "model": "gpt-4.1-mini",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "enabled_features": ["component_creation", "weekly_recaps"],
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "api_key_set": False,
    }

    follow_up = await client.get("/v1/me/profile/llm")
    assert follow_up.status_code == 200
    assert follow_up.json() == response.json()


@pytest.mark.asyncio
async def test_profile_llm_rejects_unknown_provider(client: AsyncClient) -> None:
    response = await client.put(
        "/v1/me/profile/llm",
        json={"provider": "bad-provider"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_profile_llm_invalid_key_ping_returns_422(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _reject_key(**_: Any) -> None:
        raise LLMKeyValidationError("The provider rejected this key.")

    monkeypatch.setattr(profile_router, "validate_api_key", _reject_key)

    response = await client.put(
        "/v1/me/profile/llm",
        json={
            "enabled_features": ["component_creation"],
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "bad-key",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "LLM_KEY_INVALID"
