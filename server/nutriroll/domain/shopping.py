"""Shopping-list math — vision §"Logic 7. Pricing & shopping math".

Pure function: given a list of component-quantities (per portion times portions),
existing pantry stock, and a price book, returns ShoppingListItems with
``packs_to_buy`` rounded *up* once at the list level.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from uuid import UUID

from nutriroll.domain.component import Component
from nutriroll.domain.pantry import PantryItem
from nutriroll.domain.store import SupermarketPrice


@dataclass(frozen=True, slots=True)
class ShoppingDemand:
    """How many grams (or ml or pieces) of one component we need in total."""

    component: Component
    quantity_needed: float


@dataclass(frozen=True, slots=True)
class ShoppingListItem:
    component: Component
    quantity_needed: float
    quantity_available_in_pantry: float
    quantity_to_buy: float
    """Demand minus pantry stock, never negative."""
    pack_size: float | None
    pack_price: float | None
    packs_to_buy: int | None
    line_price: float | None
    """``packs_to_buy * pack_price`` if both are known."""


@dataclass(frozen=True, slots=True)
class ShoppingList:
    items: tuple[ShoppingListItem, ...]
    portions: int
    total_price: float
    """Sum of priced lines. Lines without a price contribute 0."""
    has_missing_prices: bool


def aggregate_demand_for_bowl(
    components: Iterable[Component], portions: int
) -> dict[UUID, ShoppingDemand]:
    """For each unique component, multiply default portion size by ``portions``.

    If a component appears more than once (e.g. two vegetable slots use the
    same vegetable), demands are summed.
    """
    if portions <= 0:
        raise ValueError("portions must be > 0")
    demands: dict[UUID, ShoppingDemand] = {}
    for component in components:
        per_portion = component.default_portion.value
        total = per_portion * portions
        existing = demands.get(component.id)
        if existing is None:
            demands[component.id] = ShoppingDemand(component, total)
        else:
            demands[component.id] = ShoppingDemand(component, existing.quantity_needed + total)
    return demands


def build_shopping_list(
    demands: Mapping[UUID, ShoppingDemand],
    *,
    portions: int,
    prices: Mapping[UUID, SupermarketPrice] | None = None,
    pantry: Iterable[PantryItem] = (),
) -> ShoppingList:
    """Combine demand + pantry + prices into a ShoppingList.

    Pantry units are *not* converted across unit systems — we only subtract
    pantry stock for components where the unit matches the component's
    default portion unit.
    """
    if portions <= 0:
        raise ValueError("portions must be > 0")

    available: dict[UUID, float] = {}
    for item in pantry:
        available[item.component_id] = available.get(item.component_id, 0.0) + (
            item.quantity if item.unit == _unit_of(demands.get(item.component_id)) else 0.0
        )

    items: list[ShoppingListItem] = []
    total = 0.0
    has_missing = False
    for component_id, demand in demands.items():
        on_hand = available.get(component_id, 0.0)
        to_buy = max(demand.quantity_needed - on_hand, 0.0)
        price = prices.get(component_id) if prices else None
        if price is None:
            has_missing = True
            items.append(
                ShoppingListItem(
                    component=demand.component,
                    quantity_needed=demand.quantity_needed,
                    quantity_available_in_pantry=on_hand,
                    quantity_to_buy=to_buy,
                    pack_size=None,
                    pack_price=None,
                    packs_to_buy=None,
                    line_price=None,
                )
            )
            continue
        packs = math.ceil(to_buy / price.pack_size) if to_buy > 0 else 0
        line_price = packs * price.pack_price
        total += line_price
        items.append(
            ShoppingListItem(
                component=demand.component,
                quantity_needed=demand.quantity_needed,
                quantity_available_in_pantry=on_hand,
                quantity_to_buy=to_buy,
                pack_size=price.pack_size,
                pack_price=price.pack_price,
                packs_to_buy=packs,
                line_price=line_price,
            )
        )
    items.sort(key=lambda i: i.component.name.lower())
    return ShoppingList(
        items=tuple(items),
        portions=portions,
        total_price=round(total, 2),
        has_missing_prices=has_missing,
    )


def _unit_of(demand: ShoppingDemand | None) -> str | None:
    if demand is None:
        return None
    return demand.component.default_portion.unit.value
