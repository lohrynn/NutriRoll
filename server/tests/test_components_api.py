from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


def _valid_payload(**overrides: Any) -> dict[str, Any]:
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
            {
                "method": "steam",
                "approx_minutes": 30,
                "can_cook_with_others": True,
                "notes": None,
            },
        ],
        "flavor_tags": ["nutty"],
        "dietary_tags": ["vegan", "gluten_free"],
        "allergens": [],
        "shelf_life_days": 365,
        "blacklisted": False,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_list_empty(client: AsyncClient) -> None:
    response = await client.get("/v1/components")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_create_then_get(client: AsyncClient) -> None:
    create = await client.post("/v1/components", json=_valid_payload())
    assert create.status_code == 201, create.text
    created = create.json()
    assert created["name"] == "Brown rice"
    assert created["category"] == "base"
    assert "id" in created

    fetched = await client.get(f"/v1/components/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_create_duplicate_name_returns_409(client: AsyncClient) -> None:
    payload = _valid_payload()
    first = await client.post("/v1/components", json=payload)
    assert first.status_code == 201
    second = await client.post("/v1/components", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_default_method_must_be_listed(client: AsyncClient) -> None:
    bad = _valid_payload(default_cooking_method="roast")
    bad["cooking_methods"] = [
        {
            "method": "boil",
            "approx_minutes": 25,
            "can_cook_with_others": False,
            "notes": None,
        }
    ]
    response = await client.post("/v1/components", json=bad)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_method_must_be_allowed_for_category(client: AsyncClient) -> None:
    bad = _valid_payload(
        category="sauce",
        name="Weird sauce",
        default_cooking_method="roast",
        cooking_methods=[
            {
                "method": "roast",
                "approx_minutes": 5,
                "can_cook_with_others": False,
                "notes": None,
            }
        ],
    )
    response = await client.post("/v1/components", json=bad)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_filter_by_category(client: AsyncClient) -> None:
    base_payload = _valid_payload()
    veg_payload = _valid_payload(
        category="vegetable",
        name="Spinach",
        default_cooking_method="raw",
        cooking_methods=[
            {
                "method": "raw",
                "approx_minutes": 0,
                "can_cook_with_others": True,
                "notes": None,
            }
        ],
    )
    assert (await client.post("/v1/components", json=base_payload)).status_code == 201
    assert (await client.post("/v1/components", json=veg_payload)).status_code == 201

    only_veg = await client.get("/v1/components", params={"category": "vegetable"})
    assert only_veg.status_code == 200
    body = only_veg.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Spinach"


@pytest.mark.asyncio
async def test_update_replaces_fields(client: AsyncClient) -> None:
    create = await client.post("/v1/components", json=_valid_payload())
    component_id = create.json()["id"]

    updated_payload = _valid_payload(
        name="Brown rice (long grain)",
        flavor_tags=["nutty", "earthy"],
    )
    response = await client.put(f"/v1/components/{component_id}", json=updated_payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Brown rice (long grain)"
    assert body["flavor_tags"] == ["nutty", "earthy"]


@pytest.mark.asyncio
async def test_delete(client: AsyncClient) -> None:
    create = await client.post("/v1/components", json=_valid_payload())
    component_id = create.json()["id"]
    delete = await client.delete(f"/v1/components/{component_id}")
    assert delete.status_code == 204
    missing = await client.get(f"/v1/components/{component_id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_get_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.get("/v1/components/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
