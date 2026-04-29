from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from nutriroll.api.routers import components as components_router
from nutriroll.domain.component import (
    Category,
    Component,
    CookingMethod,
    CookingMethodSpec,
    Macros,
    Portion,
    PortionUnit,
)
from nutriroll.domain.llm_component_builder import LLMBuildError, LLMGeneratedComponent


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


def _generated_component(name: str = "Toasted quinoa") -> Component:
    return Component(
        id=uuid4(),
        category=Category.BASE,
        name=name,
        image_url=None,
        macros_per_100g=Macros(kcal=120, carbs_g=21, protein_g=4.4, fat_g=1.9, fiber_g=2.8),
        default_portion=Portion(value=85, unit=PortionUnit.GRAM),
        default_cooking_method=CookingMethod.TOAST,
        cooking_methods=(
            CookingMethodSpec(
                method=CookingMethod.TOAST,
                approx_minutes=15,
                can_cook_with_others=True,
                notes="Toast after simmering for crunch.",
            ),
        ),
        flavor_tags=("nutty", "crunchy"),
        dietary_tags=("vegan",),
        allergens=(),
        shelf_life_days=4,
        seasonal_availability="year-round",
        blacklisted=False,
    )


@pytest.mark.asyncio
async def test_generate_component_returns_structured_payload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    components_router._generate_rate_limit_cache.clear()

    class _FakeBuilder:
        model = "test-model"

        def build_from_prompt(
            self, prompt: str, profile: object | None
        ) -> LLMGeneratedComponent:
            assert prompt == "a crunchy toasted quinoa base"
            return LLMGeneratedComponent(
                component=_generated_component(),
                raw_llm_output='{"name":"Toasted quinoa"}',
                confidence=0.88,
            )

    monkeypatch.setattr(components_router, "LLMComponentBuilder", _FakeBuilder)

    response = await client.post(
        "/v1/components/generate",
        json={"prompt": "a crunchy toasted quinoa base"},
        headers={"x-device-id": "device-1"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["component"]["name"] == "Toasted quinoa"
    assert body["component"]["seasonal_availability"] == "year-round"
    assert body["confidence"] == pytest.approx(0.88)


@pytest.mark.asyncio
async def test_generate_component_returns_problem_detail_on_builder_error(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    components_router._generate_rate_limit_cache.clear()

    class _FakeBuilder:
        model = "test-model"

        def build_from_prompt(self, prompt: str, profile: object | None) -> LLMGeneratedComponent:
            raise LLMBuildError("The AI response was incomplete.")

    monkeypatch.setattr(components_router, "LLMComponentBuilder", _FakeBuilder)

    response = await client.post(
        "/v1/components/generate",
        json={"prompt": "bad prompt"},
        headers={"x-device-id": "device-2"},
    )
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "The AI response was incomplete."


@pytest.mark.asyncio
async def test_generate_component_rate_limits_per_device(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    components_router._generate_rate_limit_cache.clear()

    class _FakeBuilder:
        model = "test-model"

        def build_from_prompt(self, prompt: str, profile: object | None) -> LLMGeneratedComponent:
            return LLMGeneratedComponent(
                component=_generated_component("Quick quinoa"),
                raw_llm_output='{"name":"Quick quinoa"}',
                confidence=0.8,
            )

    monkeypatch.setattr(components_router, "LLMComponentBuilder", _FakeBuilder)

    first = await client.post(
        "/v1/components/generate",
        json={"prompt": "first"},
        headers={"x-device-id": "device-3"},
    )
    second = await client.post(
        "/v1/components/generate",
        json={"prompt": "second"},
        headers={"x-device-id": "device-3"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
