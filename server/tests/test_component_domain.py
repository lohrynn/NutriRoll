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
