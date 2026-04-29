from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


def _topping_payload() -> dict[str, Any]:
    return {
        "category": "topping",
        "name": "Crunchy Chickpeas",
        "image_url": None,
        "macros_per_100g": {
            "kcal": 180.0,
            "carbs_g": 20.0,
            "protein_g": 8.0,
            "fat_g": 6.0,
            "fiber_g": 5.0,
        },
        "default_portion": {"value": 30.0, "unit": "g"},
        "default_cooking_method": "roast",
        "cooking_methods": [
            {
                "method": "roast",
                "approx_minutes": 20,
                "can_cook_with_others": True,
                "notes": None,
            }
        ],
        "flavor_tags": ["crunchy"],
        "dietary_tags": ["vegan"],
        "allergens": [],
        "shelf_life_days": 365,
        "blacklisted": False,
    }


def _base_payload() -> dict[str, Any]:
    return {
        "category": "base",
        "name": "Brown rice",
        "image_url": None,
        "macros_per_100g": {
            "kcal": 130.0,
            "carbs_g": 25.0,
            "protein_g": 4.0,
            "fat_g": 1.0,
            "fiber_g": 2.0,
        },
        "default_portion": {"value": 80.0, "unit": "g"},
        "default_cooking_method": "boil",
        "cooking_methods": [
            {
                "method": "boil",
                "approx_minutes": 25,
                "can_cook_with_others": False,
                "notes": None,
            }
        ],
        "flavor_tags": ["mild"],
        "dietary_tags": ["vegan"],
        "allergens": [],
        "shelf_life_days": 365,
        "blacklisted": False,
    }


def _veg_payload() -> dict[str, Any]:
    return {
        "category": "vegetable",
        "name": "Broccoli",
        "image_url": None,
        "macros_per_100g": {
            "kcal": 35.0,
            "carbs_g": 7.0,
            "protein_g": 2.4,
            "fat_g": 0.4,
            "fiber_g": 2.6,
        },
        "default_portion": {"value": 80.0, "unit": "g"},
        "default_cooking_method": "steam",
        "cooking_methods": [
            {
                "method": "steam",
                "approx_minutes": 5,
                "can_cook_with_others": True,
                "notes": None,
            }
        ],
        "flavor_tags": ["mild"],
        "dietary_tags": ["vegan"],
        "allergens": [],
        "shelf_life_days": 7,
        "blacklisted": False,
    }


def _sauce_payload() -> dict[str, Any]:
    return {
        "category": "sauce",
        "name": "Tahini",
        "image_url": None,
        "macros_per_100g": {
            "kcal": 595.0,
            "carbs_g": 21.0,
            "protein_g": 17.0,
            "fat_g": 53.0,
            "fiber_g": 9.0,
        },
        "default_portion": {"value": 20.0, "unit": "g"},
        "default_cooking_method": "blend_cold",
        "cooking_methods": [
            {
                "method": "blend_cold",
                "approx_minutes": 2,
                "can_cook_with_others": True,
                "notes": None,
            }
        ],
        "flavor_tags": ["nutty"],
        "dietary_tags": ["vegan"],
        "allergens": ["sesame"],
        "shelf_life_days": 365,
        "blacklisted": False,
    }


async def _seed_pool(client: AsyncClient) -> None:
    for payload in (
        _base_payload(),
        _veg_payload(),
        _sauce_payload(),
        _topping_payload(),
    ):
        response = await client.post("/v1/components", json=payload)
        assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_roll_returns_one_per_slot(client: AsyncClient) -> None:
    await _seed_pool(client)
    body = {
        "slots": [
            {"category": "base", "count": 1},
            {"category": "vegetable", "count": 1},
            {"category": "sauce", "count": 1},
            {"category": "topping", "count": 1},
        ],
        "time_budget_min": 30,
        "seed": 42,
    }
    response = await client.post("/v1/roll", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["slots"]) == 4
    cats = [s["component"]["category"] for s in data["slots"]]
    assert cats == ["base", "vegetable", "sauce", "topping"]
    for slot in data["slots"]:
        assert slot["reasons"]


@pytest.mark.asyncio
async def test_roll_is_deterministic(client: AsyncClient) -> None:
    await _seed_pool(client)
    body = {
        "slots": [{"category": "base", "count": 1}],
        "seed": 7,
    }
    a = await client.post("/v1/roll", json=body)
    b = await client.post("/v1/roll", json=body)
    assert a.status_code == 200
    assert b.status_code == 200
    assert a.json() == b.json()


@pytest.mark.asyncio
async def test_roll_respects_allergen_exclusion(client: AsyncClient) -> None:
    await _seed_pool(client)
    body = {
        "slots": [{"category": "sauce", "count": 1}],
        "allergens_excluded": ["sesame"],
        "seed": 1,
    }
    response = await client.post("/v1/roll", json=body)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "empty_candidate_pool"


@pytest.mark.asyncio
async def test_roll_respects_blacklist(client: AsyncClient) -> None:
    await _seed_pool(client)
    list_resp = await client.get("/v1/components", params={"category": "base"})
    base_id = list_resp.json()["items"][0]["id"]
    body = {
        "slots": [{"category": "base", "count": 1}],
        "blacklisted_ids": [base_id],
        "seed": 1,
    }
    response = await client.post("/v1/roll", json=body)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reroll_slot_returns_single_slot(client: AsyncClient) -> None:
    await _seed_pool(client)
    list_resp = await client.get("/v1/components", params={"category": "base"})
    base_id = list_resp.json()["items"][0]["id"]
    body = {
        "request": {
            "slots": [{"category": "base", "count": 1}],
            "seed": 5,
        },
        "slot_category": "base",
        "exclude_component_ids": [base_id],
    }
    response = await client.post("/v1/roll/slot", json=body)
    # Only one base in the pool — exclusion empties it.
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_roll_validates_request_body(client: AsyncClient) -> None:
    response = await client.post("/v1/roll", json={"slots": []})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_roll_pantry_bonus_surfaces_expiring_components(client: AsyncClient) -> None:
    """Components in pantry with near expiry should consistently win the slot."""
    await _seed_pool(client)
    # Add an extra base so the pool actually contains a choice.
    extra_base = {
        **_base_payload(),
        "name": "Quinoa",
    }
    response = await client.post("/v1/components", json=extra_base)
    assert response.status_code == 201

    base_list = await client.get("/v1/components", params={"category": "base"})
    assert base_list.status_code == 200
    bases = base_list.json()["items"]
    target = next(b for b in bases if b["name"] == "Quinoa")
    target_id: str = target["id"]

    # Mark target as expiring tomorrow.
    from datetime import date, timedelta

    expires = (date.today() + timedelta(days=1)).isoformat()
    pantry_post = await client.post(
        "/v1/pantry",
        json={
            "component_id": target_id,
            "quantity": 100.0,
            "unit": "g",
            "opened": False,
            "expires_at": expires,
        },
    )
    assert pantry_post.status_code == 201

    # Roll many times with high pantry weight; expiring item should dominate.
    hits = 0
    for seed in range(10):
        response = await client.post(
            "/v1/roll",
            json={
                "slots": [{"category": "base", "count": 1}],
                "weights": {"pantry_bonus": 0.95},
                "temperature": 0.1,
                "seed": seed,
            },
        )
        assert response.status_code == 200
        if response.json()["slots"][0]["component"]["id"] == target_id:
            hits += 1
    assert hits >= 8, f"expected pantry-expiring item to dominate, hit {hits}/10"
