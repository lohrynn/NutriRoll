from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


def _component_payload(name: str = "Brown rice") -> dict[str, Any]:
    return {
        "category": "base",
        "name": name,
        "image_url": None,
        "macros_per_100g": {
            "kcal": 123.0,
            "carbs_g": 25.0,
            "protein_g": 2.5,
            "fat_g": 1.0,
            "fiber_g": 1.8,
        },
        "default_portion": {"value": 80.0, "unit": "g"},
        "default_cooking_method": "boil",
        "cooking_methods": [
            {
                "method": "boil",
                "approx_minutes": 25,
                "can_cook_with_others": False,
                "notes": None,
            },
        ],
        "flavor_tags": [],
        "dietary_tags": [],
        "allergens": [],
        "shelf_life_days": 365,
        "blacklisted": False,
    }


@pytest.mark.asyncio
async def test_build_shopping_list_with_prices(client: AsyncClient) -> None:
    rice = (await client.post("/v1/components", json=_component_payload("Rice"))).json()
    store = (await client.post("/v1/stores", json={"name": "REWE", "is_primary": True})).json()
    await client.put(
        f"/v1/stores/{store['id']}/prices",
        json={"component_id": rice["id"], "pack_size": 500.0, "pack_price": 2.0},
    )

    response = await client.post(
        "/v1/shopping-list",
        json={
            "component_ids": [rice["id"]],
            "portions": 4,
            "store_id": store["id"],
            "use_pantry": False,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["quantity_needed"] == 320.0
    assert item["packs_to_buy"] == 1
    assert item["line_price"] == 2.0
    assert body["total_price"] == 2.0
    assert body["has_missing_prices"] is False


@pytest.mark.asyncio
async def test_build_without_store_marks_missing(client: AsyncClient) -> None:
    rice = (await client.post("/v1/components", json=_component_payload("Rice"))).json()
    response = await client.post(
        "/v1/shopping-list",
        json={
            "component_ids": [rice["id"]],
            "portions": 1,
            "use_pantry": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["has_missing_prices"] is True
    assert body["items"][0]["line_price"] is None


@pytest.mark.asyncio
async def test_unknown_component_404(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/shopping-list",
        json={
            "component_ids": ["00000000-0000-0000-0000-000000000000"],
            "portions": 1,
        },
    )
    assert response.status_code == 404
