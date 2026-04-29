"""Pure-function tests for the recipe builder."""

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
from nutriroll.domain.recipe import (
    IncompatibleForcedMethodError,
    build_recipe,
)


def _comp(
    *,
    category: Category,
    name: str,
    methods: tuple[CookingMethodSpec, ...],
    default: CookingMethod,
) -> Component:
    return Component(
        id=uuid4(),
        category=category,
        name=name,
        macros_per_100g=Macros(kcal=100, carbs_g=10, protein_g=5, fat_g=3, fiber_g=2),
        default_portion=Portion(value=80, unit=PortionUnit.GRAM),
        default_cooking_method=default,
        cooking_methods=methods,
    )


def _base() -> Component:
    return _comp(
        category=Category.BASE,
        name="Brown rice",
        methods=(
            CookingMethodSpec(
                method=CookingMethod.BOIL,
                approx_minutes=25,
                can_cook_with_others=False,
            ),
        ),
        default=CookingMethod.BOIL,
    )


def _broccoli() -> Component:
    return _comp(
        category=Category.VEGETABLE,
        name="Broccoli",
        methods=(
            CookingMethodSpec(
                method=CookingMethod.STEAM,
                approx_minutes=5,
                can_cook_with_others=True,
            ),
        ),
        default=CookingMethod.STEAM,
    )


def _carrots() -> Component:
    return _comp(
        category=Category.VEGETABLE,
        name="Carrots",
        methods=(
            CookingMethodSpec(
                method=CookingMethod.STEAM,
                approx_minutes=8,
                can_cook_with_others=True,
            ),
            CookingMethodSpec(
                method=CookingMethod.ROAST,
                approx_minutes=20,
                can_cook_with_others=True,
            ),
        ),
        default=CookingMethod.STEAM,
    )


def _sauce() -> Component:
    return _comp(
        category=Category.SAUCE,
        name="Tahini",
        methods=(
            CookingMethodSpec(
                method=CookingMethod.BLEND_COLD,
                approx_minutes=2,
                can_cook_with_others=True,
            ),
        ),
        default=CookingMethod.BLEND_COLD,
    )


def _topping() -> Component:
    return _comp(
        category=Category.TOPPING,
        name="Crunchy chickpeas",
        methods=(
            CookingMethodSpec(
                method=CookingMethod.ROAST,
                approx_minutes=20,
                can_cook_with_others=True,
            ),
            CookingMethodSpec(
                method=CookingMethod.NO_PREP,
                approx_minutes=0,
                can_cook_with_others=True,
            ),
        ),
        default=CookingMethod.NO_PREP,
    )


def test_build_recipe_orders_blocks_longest_first() -> None:
    recipe = build_recipe([_base(), _broccoli(), _sauce(), _topping()])
    minutes = [b.total_minutes for b in recipe.blocks]
    assert minutes == sorted(minutes, reverse=True)
    assert recipe.total_minutes == 25  # base wins
    cats = [b.category for b in recipe.blocks]
    assert cats[0] is Category.BASE


def test_build_recipe_groups_compatible_vegetables() -> None:
    recipe = build_recipe([_broccoli(), _carrots()])
    veg_blocks = [b for b in recipe.blocks if b.category is Category.VEGETABLE]
    assert len(veg_blocks) == 1
    block = veg_blocks[0]
    assert block.method is CookingMethod.STEAM
    assert {c.name for c in block.components} == {"Broccoli", "Carrots"}
    assert block.total_minutes == 8  # the longest steam time
    # Carrots (8 min) starts at 0; Broccoli (5 min) starts at offset 3.
    offsets = sorted(s.offset_min for s in block.steps)
    assert offsets == [0, 3]


def _raw_pepper() -> Component:
    return _comp(
        category=Category.VEGETABLE,
        name="Bell pepper",
        methods=(
            CookingMethodSpec(
                method=CookingMethod.RAW,
                approx_minutes=2,
                can_cook_with_others=True,
            ),
        ),
        default=CookingMethod.RAW,
    )


def test_build_recipe_does_not_group_when_methods_differ() -> None:
    recipe = build_recipe([_broccoli(), _raw_pepper()])
    veg_blocks = [b for b in recipe.blocks if b.category is Category.VEGETABLE]
    # Different default methods → two separate blocks, not grouped.
    assert len(veg_blocks) == 2
    methods = {b.method for b in veg_blocks}
    assert methods == {CookingMethod.STEAM, CookingMethod.RAW}


def test_build_recipe_forced_method_incompatible_raises() -> None:
    with pytest.raises(IncompatibleForcedMethodError) as exc_info:
        build_recipe(
            [_broccoli()],
            forced_methods={Category.VEGETABLE: CookingMethod.ROAST},
        )
    assert exc_info.value.method is CookingMethod.ROAST
    assert exc_info.value.component.name == "Broccoli"


def test_build_recipe_forced_method_used_when_compatible() -> None:
    recipe = build_recipe(
        [_carrots()],
        forced_methods={Category.VEGETABLE: CookingMethod.ROAST},
    )
    veg = next(b for b in recipe.blocks if b.category is Category.VEGETABLE)
    assert veg.method is CookingMethod.ROAST
    assert veg.total_minutes == 20


def test_build_recipe_empty_components_raises() -> None:
    with pytest.raises(ValueError):
        build_recipe([])


def test_build_recipe_single_component_makes_one_block() -> None:
    recipe = build_recipe([_sauce()])
    assert len(recipe.blocks) == 1
    block = recipe.blocks[0]
    assert block.category is Category.SAUCE
    assert block.method is CookingMethod.BLEND_COLD
    assert block.total_minutes == 2
    assert len(block.steps) == 1
    assert block.steps[0].offset_min == 0
