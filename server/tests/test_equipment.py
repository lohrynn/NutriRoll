"""Phase 13 — equipment hard filter and meta exposure."""

from __future__ import annotations

from uuid import uuid4

from nutriroll.domain.component import (
    Category,
    Component,
    CookingMethod,
    CookingMethodSpec,
    Macros,
    Portion,
    PortionUnit,
)
from nutriroll.domain.equipment import (
    DEFAULT_EQUIPMENT,
    METHOD_REQUIREMENTS,
    Equipment,
    component_is_equipment_feasible,
    method_is_available,
)


def _comp(methods: list[CookingMethod]) -> Component:
    return Component(
        id=uuid4(),
        name="x",
        category=Category.BASE,
        macros_per_100g=Macros(kcal=100, carbs_g=20, protein_g=4, fat_g=1, fiber_g=2),
        default_portion=Portion(value=100, unit=PortionUnit.GRAM),
        default_cooking_method=methods[0],
        cooking_methods=tuple(
            CookingMethodSpec(method=m, approx_minutes=10) for m in methods
        ),
    )


def test_method_is_available_with_empty_set_is_true() -> None:
    # Back-compat: empty available set means "all available".
    assert method_is_available(CookingMethod.ROAST, frozenset())


def test_method_is_available_respects_requirements() -> None:
    assert method_is_available(CookingMethod.ROAST, frozenset({Equipment.OVEN}))
    assert not method_is_available(CookingMethod.ROAST, frozenset({Equipment.STOVETOP}))
    # No-equipment methods are always allowed.
    assert method_is_available(CookingMethod.RAW, frozenset({Equipment.OVEN}))


def test_component_filtered_when_no_method_is_doable() -> None:
    only_air_fry = _comp([CookingMethod.AIR_FRY])
    has_one_doable = _comp([CookingMethod.AIR_FRY, CookingMethod.PAN_FRY])
    assert not component_is_equipment_feasible(only_air_fry, frozenset({Equipment.STOVETOP}))
    assert component_is_equipment_feasible(has_one_doable, frozenset({Equipment.STOVETOP}))


def test_default_equipment_covers_common_kitchen() -> None:
    assert Equipment.OVEN in DEFAULT_EQUIPMENT
    assert Equipment.STOVETOP in DEFAULT_EQUIPMENT
    assert Equipment.MICROWAVE in DEFAULT_EQUIPMENT


def test_method_requirements_is_complete_for_every_cooking_method() -> None:
    # Anti-regression: forgetting to map a new CookingMethod silently lets it
    # slip past the equipment filter — list every method explicitly.
    for method in CookingMethod:
        assert method in METHOD_REQUIREMENTS, f"missing requirement for {method!r}"
