"""HTTP tests for the /v1/recipe endpoint."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


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


def _broccoli_payload() -> dict[str, Any]:
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


def _carrots_payload() -> dict[str, Any]:
    return {
        "category": "vegetable",
        "name": "Carrots",
        "image_url": None,
        "macros_per_100g": {
            "kcal": 41.0,
            "carbs_g": 10.0,
            "protein_g": 0.9,
            "fat_g": 0.2,
            "fiber_g": 2.8,
        },
        "default_portion": {"value": 80.0, "unit": "g"},
        "default_cooking_method": "steam",
        "cooking_methods": [
            {
                "method": "steam",
                "approx_minutes": 8,
                "can_cook_with_others": True,
                "notes": None,
            },
            {
                "method": "roast",
                "approx_minutes": 20,
                "can_cook_with_others": True,
                "notes": None,
            },
        ],
        "flavor_tags": ["sweet"],
        "dietary_tags": ["vegan"],
        "allergens": [],
        "shelf_life_days": 14,
        "blacklisted": False,
    }


async def _create(client: AsyncClient, payload: dict[str, Any]) -> str:
    response = await client.post("/v1/components", json=payload)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


@pytest.mark.asyncio
async def test_recipe_returns_blocks_sorted_longest_first(
    client: AsyncClient,
) -> None:
    base_id = await _create(client, _base_payload())
    veg_id = await _create(client, _broccoli_payload())
    response = await client.post(
        "/v1/recipe",
        json={"component_ids": [veg_id, base_id]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    minutes = [b["total_minutes"] for b in body["blocks"]]
    assert minutes == sorted(minutes, reverse=True)
    assert body["total_minutes"] == 25


@pytest.mark.asyncio
async def test_recipe_groups_compatible_vegetables(client: AsyncClient) -> None:
    veg_a = await _create(client, _broccoli_payload())
    veg_b = await _create(client, _carrots_payload())
    response = await client.post(
        "/v1/recipe",
        json={"component_ids": [veg_a, veg_b]},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["blocks"]) == 1
    block = body["blocks"][0]
    assert block["method"] == "steam"
    assert {c["name"] for c in block["components"]} == {"Broccoli", "Carrots"}
    assert block["total_minutes"] == 8
    offsets = sorted(s["offset_min"] for s in block["steps"])
    assert offsets == [0, 3]


@pytest.mark.asyncio
async def test_recipe_unknown_component_404(client: AsyncClient) -> None:
    bogus = str(uuid4())
    response = await client.post(
        "/v1/recipe",
        json={"component_ids": [bogus]},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "component_not_found"


@pytest.mark.asyncio
async def test_recipe_incompatible_forced_method_422(
    client: AsyncClient,
) -> None:
    # Broccoli only supports steam; force roast → 422.
    veg_id = await _create(client, _broccoli_payload())
    response = await client.post(
        "/v1/recipe",
        json={
            "component_ids": [veg_id],
            "forced_methods": {"vegetable": "roast"},
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "incompatible_forced_method"


@pytest.mark.asyncio
async def test_recipe_validates_request(client: AsyncClient) -> None:
    response = await client.post("/v1/recipe", json={"component_ids": []})
    assert response.status_code == 422
