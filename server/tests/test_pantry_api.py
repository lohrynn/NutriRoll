from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


def _component_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "category": "base",
        "name": "Brown rice",
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
    payload.update(overrides)
    return payload


async def _create_component(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post("/v1/components", json=_component_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_list_empty(client: AsyncClient) -> None:
    response = await client.get("/v1/pantry")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_create_then_list(client: AsyncClient) -> None:
    component = await _create_component(client)
    payload = {
        "component_id": component["id"],
        "quantity": 200.0,
        "unit": "g",
        "opened": True,
        "expires_at": "2026-12-31",
    }
    create = await client.post("/v1/pantry", json=payload)
    assert create.status_code == 201, create.text
    created = create.json()
    assert created["component_id"] == component["id"]
    assert created["quantity"] == 200.0
    assert created["opened"] is True
    assert created["expires_at"] == "2026-12-31"

    listed = await client.get("/v1/pantry")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == created["id"]


@pytest.mark.asyncio
async def test_create_unknown_component_returns_404(client: AsyncClient) -> None:
    payload = {
        "component_id": "00000000-0000-0000-0000-000000000000",
        "quantity": 100.0,
        "unit": "g",
    }
    response = await client.post("/v1/pantry", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "component_not_found"


@pytest.mark.asyncio
async def test_update_and_delete(client: AsyncClient) -> None:
    component = await _create_component(client)
    create = await client.post(
        "/v1/pantry",
        json={"component_id": component["id"], "quantity": 100.0, "unit": "g"},
    )
    item_id = create.json()["id"]

    updated = await client.put(
        f"/v1/pantry/{item_id}",
        json={
            "component_id": component["id"],
            "quantity": 50.0,
            "unit": "g",
            "opened": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["quantity"] == 50.0
    assert updated.json()["opened"] is True

    deleted = await client.delete(f"/v1/pantry/{item_id}")
    assert deleted.status_code == 204

    after = await client.get("/v1/pantry")
    assert after.json()["total"] == 0


@pytest.mark.asyncio
async def test_quantity_must_be_non_negative(client: AsyncClient) -> None:
    component = await _create_component(client)
    response = await client.post(
        "/v1/pantry",
        json={"component_id": component["id"], "quantity": -1.0, "unit": "g"},
    )
    assert response.status_code == 422
