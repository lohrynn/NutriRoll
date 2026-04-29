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
async def test_store_crud_and_primary(client: AsyncClient) -> None:
    listed = await client.get("/v1/stores")
    assert listed.status_code == 200
    assert listed.json() == {"items": [], "total": 0}

    a = await client.post(
        "/v1/stores",
        json={"name": "Store A", "location": "Center", "is_primary": True},
    )
    assert a.status_code == 201
    b = await client.post(
        "/v1/stores",
        json={"name": "Store B", "location": None, "is_primary": True},
    )
    assert b.status_code == 201

    listed = await client.get("/v1/stores")
    items = listed.json()["items"]
    primary = [s for s in items if s["is_primary"]]
    assert len(primary) == 1
    assert primary[0]["name"] == "Store B"


@pytest.mark.asyncio
async def test_duplicate_store_name_409(client: AsyncClient) -> None:
    a = await client.post("/v1/stores", json={"name": "Edeka", "is_primary": False})
    assert a.status_code == 201
    dup = await client.post("/v1/stores", json={"name": "Edeka", "is_primary": False})
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_price_upsert_and_list(client: AsyncClient) -> None:
    store = await client.post("/v1/stores", json={"name": "REWE", "is_primary": True})
    store_id = store.json()["id"]
    component = await client.post("/v1/components", json=_component_payload())
    component_id = component.json()["id"]

    first = await client.put(
        f"/v1/stores/{store_id}/prices",
        json={"component_id": component_id, "pack_size": 500.0, "pack_price": 2.49},
    )
    assert first.status_code == 200
    first_id = first.json()["id"]

    # upsert again with new price
    second = await client.put(
        f"/v1/stores/{store_id}/prices",
        json={"component_id": component_id, "pack_size": 500.0, "pack_price": 1.99},
    )
    assert second.status_code == 200
    assert second.json()["id"] == first_id  # same row updated
    assert second.json()["pack_price"] == 1.99

    listed = await client.get(f"/v1/stores/{store_id}/prices")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


@pytest.mark.asyncio
async def test_delete_store_cascades_prices(client: AsyncClient) -> None:
    store = await client.post("/v1/stores", json={"name": "Aldi", "is_primary": False})
    store_id = store.json()["id"]
    component = await client.post("/v1/components", json=_component_payload("Quinoa"))
    component_id = component.json()["id"]
    await client.put(
        f"/v1/stores/{store_id}/prices",
        json={"component_id": component_id, "pack_size": 500.0, "pack_price": 3.99},
    )
    deleted = await client.delete(f"/v1/stores/{store_id}")
    assert deleted.status_code == 204
    after = await client.get(f"/v1/stores/{store_id}/prices")
    assert after.status_code == 404
