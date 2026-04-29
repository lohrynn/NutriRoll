"""Tests for /v1/saved and /v1/planned endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_saved_meal_crud(client: AsyncClient) -> None:
    # Empty initial list
    r = await client.get("/v1/saved")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0}

    # Create
    body: dict[str, Any] = {
        "name": "My favorite poke",
        "bowl_snapshot": {"slots": []},
        "notes": "summer staple",
    }
    r = await client.post("/v1/saved", json=body)
    assert r.status_code == 201
    created = r.json()
    assert created["name"] == "My favorite poke"
    assert created["notes"] == "summer staple"
    meal_id = created["id"]

    # List
    r = await client.get("/v1/saved")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == meal_id

    # Delete
    r = await client.delete(f"/v1/saved/{meal_id}")
    assert r.status_code == 204

    r = await client.delete(f"/v1/saved/{meal_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_saved_meal_rejects_blank_name(client: AsyncClient) -> None:
    r = await client.post("/v1/saved", json={"name": "   ", "bowl_snapshot": {}})
    assert r.status_code == 422
    r = await client.post("/v1/saved", json={"name": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_planned_meal_crud_and_range(client: AsyncClient) -> None:
    body: dict[str, Any] = {
        "planned_for": "2026-06-01",
        "slot": "lunch",
        "bowl_snapshot": {"slots": []},
    }
    r = await client.post("/v1/planned", json=body)
    assert r.status_code == 201
    created = r.json()
    assert created["status"] == "planned"
    assert created["slot"] == "lunch"
    meal_id = created["id"]

    # Range filter — inside
    r = await client.get("/v1/planned?start=2026-06-01&end=2026-06-07")
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # Range filter — outside
    r = await client.get("/v1/planned?start=2026-07-01&end=2026-07-07")
    assert r.status_code == 200
    assert r.json()["total"] == 0

    # Update: move to next day + mark cooked
    r = await client.patch(
        f"/v1/planned/{meal_id}",
        json={"planned_for": "2026-06-02", "status": "cooked"},
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["planned_for"] == "2026-06-02"
    assert updated["status"] == "cooked"

    # Delete
    r = await client.delete(f"/v1/planned/{meal_id}")
    assert r.status_code == 204

    r = await client.patch(f"/v1/planned/{meal_id}", json={"status": "skipped"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planned_meal_rejects_unknown_slot(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/planned",
        json={
            "planned_for": "2026-06-01",
            "slot": "midnight_snack",
            "bowl_snapshot": {},
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_planned_meal_portions_default_to_one(client: AsyncClient) -> None:
    """Phase 12: omitting ``portions_total`` keeps the historic single-meal shape."""
    r = await client.post(
        "/v1/planned",
        json={"planned_for": "2026-06-10", "slot": "dinner", "bowl_snapshot": {}},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["portions_total"] == 1
    assert body["portions_remaining"] == 1


@pytest.mark.asyncio
async def test_planned_meal_mark_eaten_decrements_and_completes(client: AsyncClient) -> None:
    """Phase 12: a 3-portion prep is decremented per portion; status flips at 0."""
    r = await client.post(
        "/v1/planned",
        json={
            "planned_for": "2026-06-10",
            "slot": "lunch",
            "bowl_snapshot": {},
            "portions_total": 3,
        },
    )
    assert r.status_code == 201
    created = r.json()
    assert created["portions_total"] == 3
    assert created["portions_remaining"] == 3
    assert created["status"] == "planned"
    meal_id = created["id"]

    r = await client.post(f"/v1/planned/{meal_id}/mark-eaten")
    assert r.status_code == 200
    assert r.json()["portions_remaining"] == 2
    assert r.json()["status"] == "planned"

    r = await client.post(f"/v1/planned/{meal_id}/mark-eaten")
    assert r.status_code == 200
    assert r.json()["portions_remaining"] == 1

    r = await client.post(f"/v1/planned/{meal_id}/mark-eaten")
    assert r.status_code == 200
    final = r.json()
    assert final["portions_remaining"] == 0
    assert final["status"] == "cooked"

    # Subsequent calls are no-ops (still 0, still cooked).
    r = await client.post(f"/v1/planned/{meal_id}/mark-eaten")
    assert r.status_code == 200
    assert r.json()["portions_remaining"] == 0


@pytest.mark.asyncio
async def test_planned_meal_mark_eaten_404_for_unknown_id(client: AsyncClient) -> None:
    r = await client.post("/v1/planned/00000000-0000-0000-0000-000000000000/mark-eaten")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_planned_meal_rejects_invalid_portions_total(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/planned",
        json={
            "planned_for": "2026-06-10",
            "slot": "dinner",
            "bowl_snapshot": {},
            "portions_total": 0,
        },
    )
    assert r.status_code == 422
    r = await client.post(
        "/v1/planned",
        json={
            "planned_for": "2026-06-10",
            "slot": "dinner",
            "bowl_snapshot": {},
            "portions_total": 99,
        },
    )
    assert r.status_code == 422
