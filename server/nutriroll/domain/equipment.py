"""Phase 13 — kitchen equipment.

Framework-free: pure data + functions. The roll algorithm consults
``METHOD_REQUIREMENTS`` to drop components whose every supported cooking
method requires hardware the user does not own. The meta endpoint exposes
the same map so the frontend renders the chip toggles without duplicating
the relationship.

A component is *equipment-feasible* iff at least one of its supported
cooking methods has all required equipment available, or the user has not
declared any equipment (``available_equipment`` empty = "all available",
which is the back-compat default for pre-Phase-13 profiles).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum
from types import MappingProxyType

from nutriroll.domain.component import Component, CookingMethod


class Equipment(StrEnum):
    """User-owned hardware. Single source of truth for the chip set."""

    OVEN = "oven"
    STOVETOP = "stovetop"
    MICROWAVE = "microwave"
    AIR_FRYER = "air_fryer"
    PRESSURE_COOKER = "pressure_cooker"
    BLENDER = "blender"
    GRILL = "grill"
    TOASTER = "toaster"


# Each cooking method declares the equipment a kitchen must have to use it.
# Methods that need no hardware (raw / no_prep / custom) map to an empty set
# and are always available.
_METHOD_REQUIREMENTS_RAW: dict[CookingMethod, frozenset[Equipment]] = {
    # Bases / Vegetables / Toppings
    CookingMethod.BOIL: frozenset({Equipment.STOVETOP}),
    CookingMethod.STEAM: frozenset({Equipment.STOVETOP}),
    CookingMethod.BLANCH: frozenset({Equipment.STOVETOP}),
    CookingMethod.PAN_FRY: frozenset({Equipment.STOVETOP}),
    CookingMethod.ROAST: frozenset({Equipment.OVEN}),
    CookingMethod.AIR_FRY: frozenset({Equipment.AIR_FRYER}),
    CookingMethod.GRILL: frozenset({Equipment.GRILL}),
    CookingMethod.BAKE: frozenset({Equipment.OVEN}),
    CookingMethod.TOAST: frozenset({Equipment.TOASTER}),
    CookingMethod.RAW: frozenset(),
    CookingMethod.NO_PREP: frozenset(),
    # Sauces
    CookingMethod.BLEND_COLD: frozenset({Equipment.BLENDER}),
    CookingMethod.BLEND_HOT: frozenset({Equipment.BLENDER}),
    CookingMethod.HEAT: frozenset({Equipment.STOVETOP}),
    CookingMethod.WHISK_COLD: frozenset(),
    CookingMethod.WHISK_HOT: frozenset({Equipment.STOVETOP}),
    CookingMethod.REDUCE: frozenset({Equipment.STOVETOP}),
    CookingMethod.SAUTE_SIMMER: frozenset({Equipment.STOVETOP}),
    # Toppings
    CookingMethod.CRUMBLE: frozenset(),
    # Escape hatch — allow user-defined methods even with no equipment.
    CookingMethod.CUSTOM: frozenset(),
}

METHOD_REQUIREMENTS: Mapping[CookingMethod, frozenset[Equipment]] = MappingProxyType(
    _METHOD_REQUIREMENTS_RAW
)
"""Read-only equipment requirements per cooking method."""


# Sensible default for new users / onboarding pre-fill: a typical kitchen.
DEFAULT_EQUIPMENT: frozenset[Equipment] = frozenset(
    {Equipment.OVEN, Equipment.STOVETOP, Equipment.MICROWAVE}
)


def method_is_available(method: CookingMethod, available: frozenset[Equipment]) -> bool:
    """True if the user can perform this method.

    Empty ``available`` means "I haven't declared anything" → every method
    is allowed (back-compat). Otherwise every required piece must be owned.
    """
    if not available:
        return True
    requirements = METHOD_REQUIREMENTS.get(method, frozenset())
    return requirements.issubset(available)


def component_is_equipment_feasible(
    component: Component, available: frozenset[Equipment]
) -> bool:
    """True if at least one of the component's methods is doable."""
    if not available:
        return True
    return any(method_is_available(spec.method, available) for spec in component.cooking_methods)


def filter_components_by_equipment(
    components: Iterable[Component], available: frozenset[Equipment]
) -> list[Component]:
    """Drop components whose every method requires unavailable hardware."""
    if not available:
        return list(components)
    return [c for c in components if component_is_equipment_feasible(c, available)]


__all__ = [
    "DEFAULT_EQUIPMENT",
    "METHOD_REQUIREMENTS",
    "Equipment",
    "component_is_equipment_feasible",
    "filter_components_by_equipment",
    "method_is_available",
]
