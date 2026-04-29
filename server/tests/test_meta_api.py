"""Tests for ``GET /v1/meta/components`` (M4 / M5 / M8 single source)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_meta_components_exposes_vocabulary(client: AsyncClient) -> None:
    response = await client.get("/v1/meta/components")
    assert response.status_code == 200
    body = response.json()

    assert set(body) == {
        "categories",
        "portion_units",
        "allowed_methods",
        "balanced_targets",
        "expiry_warning_days",
        "category_labels",
        "equipment",
        "method_requirements",
        "default_equipment",
        "llm_configured",
    }

    # Categories include the four canonical slot kinds.
    assert {"base", "vegetable", "sauce", "topping"}.issubset(body["categories"])

    # Allowed methods cover every category and contain known cooking methods.
    assert set(body["allowed_methods"]) == set(body["categories"])
    assert "boil" in body["allowed_methods"]["base"]

    # Expiry window is a positive integer (default 3, overridable via env var).
    assert isinstance(body["expiry_warning_days"], int)
    assert body["expiry_warning_days"] > 0

    # Category labels cover every category and are non-empty strings (M4).
    assert set(body["category_labels"]) == set(body["categories"])
    for label in body["category_labels"].values():
        assert isinstance(label, str) and label

    assert isinstance(body["llm_configured"], bool)

    # Balanced targets expose the same five macro keys per category and stay
    # in sync with the values used by `_nutrition_fit()`.
    for category in body["categories"]:
        macros = body["balanced_targets"][category]
        assert set(macros) >= {"kcal", "carbs_g", "protein_g", "fat_g", "fiber_g"}
        for value in macros.values():
            assert isinstance(value, (int, float))
            assert value >= 0
