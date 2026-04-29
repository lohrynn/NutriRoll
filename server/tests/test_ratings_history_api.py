from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_ratings(client: AsyncClient) -> None:
    bowl_id = "11111111-1111-4111-8111-111111111111"
    create = await client.post(
        "/v1/ratings",
        json={"bowl_id": bowl_id, "score": 4, "comment": "tasty"},
    )
    assert create.status_code == 201, create.text
    assert create.json()["score"] == 4

    listed = await client.get("/v1/ratings", params={"bowl_id": bowl_id})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


@pytest.mark.asyncio
async def test_score_out_of_range_422(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/ratings",
        json={"bowl_id": "11111111-1111-4111-8111-111111111111", "score": 6},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_history_event_and_list(client: AsyncClient) -> None:
    create = await client.post(
        "/v1/history",
        json={
            "kind": "rolled",
            "bowl_id": "22222222-2222-4222-8222-222222222222",
            "payload": {"slots": ["base", "veg"]},
        },
    )
    assert create.status_code == 201
    assert create.json()["kind"] == "rolled"

    listed = await client.get("/v1/history", params={"kind": "rolled"})
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["payload"]["slots"] == ["base", "veg"]


@pytest.mark.asyncio
async def test_delete_history_event(client: AsyncClient) -> None:
    create = await client.post("/v1/history", json={"kind": "saved", "payload": {}})
    event_id = create.json()["id"]
    deleted = await client.delete(f"/v1/history/{event_id}")
    assert deleted.status_code == 204
    after = await client.get("/v1/history")
    assert after.json()["total"] == 0
