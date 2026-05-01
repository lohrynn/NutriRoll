from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from nutriroll.api.routers import history as history_router
from nutriroll.domain.weekly_recap import WeeklyRecapGenerator, WeeklyRecapLLMError


def _week_start_for_today() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _component_payload(
    *,
    name: str,
    category: str,
    portion_value: float,
    portion_unit: str = "g",
    kcal: float,
) -> dict[str, Any]:
    default_method = "whisk_cold" if category == "sauce" else "boil"
    return {
        "category": category,
        "name": name,
        "image_url": None,
        "default_portion": {"value": portion_value, "unit": portion_unit},
        "macros_per_100g": {
            "kcal": kcal,
            "carbs_g": 10.0,
            "protein_g": 4.0,
            "fat_g": 2.0,
            "fiber_g": 2.0,
        },
        "default_cooking_method": default_method,
        "cooking_methods": [
            {
                "method": default_method,
                "approx_minutes": 10,
                "can_cook_with_others": True,
                "notes": None,
            }
        ],
        "flavor_tags": [],
        "dietary_tags": [],
        "allergens": [],
        "shelf_life_days": None,
        "seasonal_availability": None,
        "blacklisted": False,
    }


async def _enable_weekly_recaps(client: AsyncClient) -> None:
    current = (await client.get("/v1/me/profile")).json()
    current["llm_weekly_recap_enabled"] = True
    response = await client.put("/v1/me/profile", json=current)
    assert response.status_code == 200, response.text


async def _create_component(
    client: AsyncClient,
    *,
    name: str,
    category: str,
    portion_value: float,
    kcal: float,
) -> dict[str, Any]:
    response = await client.post(
        "/v1/components",
        json=_component_payload(
            name=name,
            category=category,
            portion_value=portion_value,
            kcal=kcal,
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_primary_store(client: AsyncClient) -> dict[str, Any]:
    response = await client.post("/v1/stores", json={"name": "REWE", "is_primary": True})
    assert response.status_code == 201, response.text
    return response.json()


async def _upsert_price(
    client: AsyncClient, *, store_id: str, component_id: str, pack_size: float, pack_price: float
) -> None:
    response = await client.put(
        f"/v1/stores/{store_id}/prices",
        json={
            "component_id": component_id,
            "pack_size": pack_size,
            "pack_price": pack_price,
        },
    )
    assert response.status_code == 200, response.text


async def _create_cooked_event(client: AsyncClient, components: list[dict[str, str]]) -> None:
    response = await client.post(
        "/v1/history",
        json={
            "kind": "cooked",
            "payload": {
                "components": components,
            },
        },
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_weekly_recap_valid_week_range_generates_stats(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_router._recap_cache.clear()
    await _enable_weekly_recaps(client)
    rice = await _create_component(
        client, name="Brown rice", category="base", portion_value=100, kcal=130
    )
    broccoli = await _create_component(
        client, name="Broccoli", category="vegetable", portion_value=150, kcal=35
    )
    tahini = await _create_component(
        client, name="Tahini sauce", category="sauce", portion_value=30, kcal=300
    )
    store = await _create_primary_store(client)
    await _upsert_price(
        client,
        store_id=store["id"],
        component_id=rice["id"],
        pack_size=500,
        pack_price=2.0,
    )
    await _upsert_price(
        client,
        store_id=store["id"],
        component_id=broccoli["id"],
        pack_size=500,
        pack_price=1.5,
    )
    await _upsert_price(
        client,
        store_id=store["id"],
        component_id=tahini["id"],
        pack_size=250,
        pack_price=3.0,
    )
    components = [
        {"id": rice["id"], "name": rice["name"]},
        {"id": broccoli["id"], "name": broccoli["name"]},
        {"id": tahini["id"], "name": tahini["name"]},
    ]
    await _create_cooked_event(client, components)
    await _create_cooked_event(client, components)

    async def _fake_llm(
        self: WeeklyRecapGenerator, **_: Any
    ) -> tuple[str, tuple[str, ...]]:
        return (
            "You cooked steadily this week and kept your bowls simple.",
            ("Repeat your favorite combo once next week.",),
        )

    monkeypatch.setattr(WeeklyRecapGenerator, "_generate_llm_copy", _fake_llm)

    response = await client.get(
        "/v1/history/recap",
        params={"week_start": _week_start_for_today().isoformat(), "generate": "true"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cached"] is False
    assert body["recap"]["summary_text"] == "You cooked steadily this week and kept your bowls simple."
    assert body["recap"]["stats"]["meals_cooked"] == 2
    assert body["recap"]["stats"]["spent_eur"] == 2.42
    assert body["recap"]["stats"]["avg_kcal"] == 272.5
    assert body["recap"]["stats"]["top_components"] == [
        "Brown rice",
        "Broccoli",
        "Tahini sauce",
    ]
    assert body["recap"]["stats"]["longest_streak"] == 1
    assert body["recap"]["stats"]["new_foods_tried"] == 3
    assert body["recap"]["suggestions"] == ["Repeat your favorite combo once next week."]


@pytest.mark.asyncio
async def test_weekly_recap_no_meals_returns_empty_state_message(client: AsyncClient) -> None:
    history_router._recap_cache.clear()
    await _enable_weekly_recaps(client)
    next_week = _week_start_for_today() + timedelta(days=7)

    response = await client.get(
        "/v1/history/recap",
        params={"week_start": next_week.isoformat(), "generate": "true"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recap"]["summary_text"].startswith("No meals were cooked this week yet.")
    assert body["recap"]["stats"]["meals_cooked"] == 0
    assert body["recap"]["stats"]["spent_eur"] == 0.0
    assert body["recap"]["stats"]["avg_kcal"] is None
    assert body["recap"]["suggestions"] == [
        "Start with one easy bowl to seed next week's recap."
    ]


@pytest.mark.asyncio
async def test_weekly_recap_llm_failure_returns_stats_only_fallback(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_router._recap_cache.clear()
    await _enable_weekly_recaps(client)
    rice = await _create_component(
        client, name="Quinoa", category="base", portion_value=90, kcal=120
    )
    broccoli = await _create_component(
        client, name="Spinach", category="vegetable", portion_value=120, kcal=23
    )
    await _create_cooked_event(
        client,
        [
            {"id": rice["id"], "name": rice["name"]},
            {"id": broccoli["id"], "name": broccoli["name"]},
        ],
    )

    async def _fail_llm(self: WeeklyRecapGenerator, **_: Any) -> tuple[str, tuple[str, ...]]:
        raise WeeklyRecapLLMError("boom")

    monkeypatch.setattr(WeeklyRecapGenerator, "_generate_llm_copy", _fail_llm)

    response = await client.get(
        "/v1/history/recap",
        params={"week_start": _week_start_for_today().isoformat(), "generate": "true"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recap"]["summary_text"].startswith("You cooked 1 meal this week")
    assert body["recap"]["stats"]["meals_cooked"] == 1
    assert body["recap"]["stats"]["new_foods_tried"] == 2
    assert body["recap"]["suggestions"][0] == (
        "Add a sturdier base or extra protein to keep meals more filling."
    )
