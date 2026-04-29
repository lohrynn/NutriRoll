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
from nutriroll.domain.pantry import PantryItem
from nutriroll.domain.shopping import (
    aggregate_demand_for_bowl,
    build_shopping_list,
)
from nutriroll.domain.store import SupermarketPrice


def _component(
    name: str, portion: float = 100.0, unit: PortionUnit = PortionUnit.GRAM
) -> Component:
    return Component(
        id=uuid4(),
        category=Category.BASE,
        name=name,
        macros_per_100g=Macros(kcal=100, carbs_g=20, protein_g=2, fat_g=1, fiber_g=2),
        default_portion=Portion(value=portion, unit=unit),
        default_cooking_method=CookingMethod.BOIL,
        cooking_methods=(CookingMethodSpec(method=CookingMethod.BOIL, approx_minutes=10),),
    )


def test_aggregate_sums_repeats() -> None:
    rice = _component("Rice", portion=80)
    veg = _component("Tomato", portion=60)
    demands = aggregate_demand_for_bowl([rice, veg, rice], portions=2)
    assert demands[rice.id].quantity_needed == 80 * 2 + 80 * 2
    assert demands[veg.id].quantity_needed == 60 * 2


def test_packs_round_up_and_total_price() -> None:
    rice = _component("Rice", portion=80)
    demands = aggregate_demand_for_bowl([rice], portions=4)  # 320 g needed
    price = SupermarketPrice(
        id=uuid4(),
        store_id=uuid4(),
        component_id=rice.id,
        pack_size=500.0,
        pack_price=2.49,
    )
    sl = build_shopping_list(demands, portions=4, prices={rice.id: price})
    assert len(sl.items) == 1
    item = sl.items[0]
    assert item.quantity_to_buy == 320.0
    assert item.packs_to_buy == 1
    assert item.line_price == 2.49
    assert sl.total_price == 2.49
    assert sl.has_missing_prices is False


def test_packs_round_up_when_demand_exceeds_one_pack() -> None:
    rice = _component("Rice", portion=80)
    demands = aggregate_demand_for_bowl([rice], portions=10)  # 800 g
    price = SupermarketPrice(
        id=uuid4(),
        store_id=uuid4(),
        component_id=rice.id,
        pack_size=500.0,
        pack_price=2.0,
    )
    sl = build_shopping_list(demands, portions=10, prices={rice.id: price})
    assert sl.items[0].packs_to_buy == 2
    assert sl.total_price == 4.0


def test_pantry_subtracts_when_units_match() -> None:
    rice = _component("Rice", portion=80, unit=PortionUnit.GRAM)
    demands = aggregate_demand_for_bowl([rice], portions=4)  # 320 g needed
    pantry = [
        PantryItem(
            id=uuid4(),
            component_id=rice.id,
            quantity=200.0,
            unit=PortionUnit.GRAM,
        )
    ]
    price = SupermarketPrice(
        id=uuid4(),
        store_id=uuid4(),
        component_id=rice.id,
        pack_size=500.0,
        pack_price=2.0,
    )
    sl = build_shopping_list(demands, portions=4, prices={rice.id: price}, pantry=pantry)
    item = sl.items[0]
    assert item.quantity_available_in_pantry == 200.0
    assert item.quantity_to_buy == 120.0
    assert item.packs_to_buy == 1


def test_missing_price_flagged() -> None:
    rice = _component("Rice")
    demands = aggregate_demand_for_bowl([rice], portions=1)
    sl = build_shopping_list(demands, portions=1, prices={})
    assert sl.has_missing_prices is True
    assert sl.items[0].line_price is None
    assert sl.total_price == 0.0
