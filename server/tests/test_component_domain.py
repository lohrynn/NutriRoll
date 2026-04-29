from __future__ import annotations

from uuid import uuid4

import pytest

from nutriroll.domain.component import (
    Category,
    Component,
    CookingMethod,
    CookingMethodSpec,
    Macros,
    Portion,
    PortionUnit,
)
from nutriroll.domain.llm_component_builder import (
    LLMBuildError,
    LLMComponentBuilder,
    _LLMResponse,
)


def _make(**overrides: object) -> Component:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "category": Category.BASE,
        "name": "Brown rice",
        "macros_per_100g": Macros(kcal=123.0, carbs_g=25.0, protein_g=2.5, fat_g=1.0, fiber_g=1.8),
        "default_portion": Portion(value=80.0, unit=PortionUnit.GRAM),
        "default_cooking_method": CookingMethod.BOIL,
        "cooking_methods": (
            CookingMethodSpec(
                method=CookingMethod.BOIL,
                approx_minutes=25,
                can_cook_with_others=False,
            ),
        ),
    }
    defaults.update(overrides)
    return Component(**defaults)  # type: ignore[arg-type]


def test_valid_component() -> None:
    c = _make()
    assert c.name == "Brown rice"


def test_empty_name_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        _make(name="   ")


def test_default_method_must_be_in_methods() -> None:
    with pytest.raises(ValueError, match="default_cooking_method"):
        _make(default_cooking_method=CookingMethod.STEAM)


def test_method_must_be_allowed_for_category() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        _make(
            category=Category.SAUCE,
            default_cooking_method=CookingMethod.BOIL,
            cooking_methods=(CookingMethodSpec(method=CookingMethod.BOIL, approx_minutes=10),),
        )


def test_duplicate_methods_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        _make(
            cooking_methods=(
                CookingMethodSpec(method=CookingMethod.BOIL, approx_minutes=25),
                CookingMethodSpec(method=CookingMethod.BOIL, approx_minutes=30),
            )
        )


def test_negative_macros_rejected() -> None:
    with pytest.raises(ValueError, match="kcal"):
        Macros(kcal=-1.0, carbs_g=0, protein_g=0, fat_g=0, fiber_g=0)


def test_zero_portion_rejected() -> None:
    with pytest.raises(ValueError, match="portion"):
        Portion(value=0, unit=PortionUnit.GRAM)


class _StubBuilder(LLMComponentBuilder):
    def __init__(self, raw_output: str, *, api_key: str = "test-key") -> None:
        super().__init__(api_key=api_key, model="test-model", base_url="https://example.test/v1")
        self._raw_output = raw_output

    def _request_component_json(self, prompt: str, profile: object) -> _LLMResponse:
        return _LLMResponse(raw_output=self._raw_output, confidence=0.91)


def test_llm_builder_happy_path() -> None:
    builder = _StubBuilder(
        """
        {
          "category": "base",
          "name": "Toasted quinoa",
          "image_url": null,
          "macros_per_100g": {
            "kcal": 120,
            "carbs_g": 21,
            "protein_g": 4.4,
            "fat_g": 1.9,
            "fiber_g": 2.8
          },
          "default_portion": { "value": 85, "unit": "g" },
          "default_cooking_method": "toast",
          "cooking_methods": [
            {
              "method": "toast",
              "approx_minutes": 15,
              "can_cook_with_others": true,
              "notes": "Toast after simmering for crunch."
            }
          ],
          "flavor_tags": ["nutty", "crunchy"],
          "dietary_tags": ["vegan", "gluten_free"],
          "allergens": [],
          "shelf_life_days": 4,
          "seasonal_availability": "year-round",
          "blacklisted": false,
          "confidence": 0.91
        }
        """
    )

    component = builder.generate_from_prompt("a crunchy toasted quinoa base")

    assert component.name == "Toasted quinoa"
    assert component.category == Category.BASE
    assert component.default_cooking_method == CookingMethod.TOAST
    assert component.default_portion.unit == PortionUnit.GRAM


def test_llm_builder_malformed_response_returns_friendly_error() -> None:
    builder = _StubBuilder('{"category":"base","name":"Broken"}')

    with pytest.raises(LLMBuildError, match="missing 'macros_per_100g'"):
        builder.generate_from_prompt("broken payload")


def test_llm_builder_missing_api_key_returns_friendly_error() -> None:
    builder = _StubBuilder("{}", api_key="")

    with pytest.raises(LLMBuildError, match="not configured"):
        builder.generate_from_prompt("quinoa")
