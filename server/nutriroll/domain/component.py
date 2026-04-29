"""Component domain — pure types and value objects.

This module is intentionally framework-free: no FastAPI, no SQLAlchemy, no
Pydantic. It captures the conceptual entity from PROJECT_VISION.md
§"Data model" and §"7. Component Editor".

Adapters (db.models, api.schemas) translate to/from these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class Category(StrEnum):
    BASE = "base"
    VEGETABLE = "vegetable"
    SAUCE = "sauce"
    TOPPING = "topping"


class PortionUnit(StrEnum):
    GRAM = "g"
    MILLILITER = "ml"
    PIECE = "pc"


class CookingMethod(StrEnum):
    # Bases / Vegetables / Toppings
    BOIL = "boil"
    STEAM = "steam"
    BLANCH = "blanch"
    PAN_FRY = "pan_fry"
    ROAST = "roast"
    AIR_FRY = "air_fry"
    GRILL = "grill"
    BAKE = "bake"
    TOAST = "toast"
    RAW = "raw"
    NO_PREP = "no_prep"
    # Sauces
    BLEND_COLD = "blend_cold"
    BLEND_HOT = "blend_hot"
    HEAT = "heat"
    WHISK_COLD = "whisk_cold"
    WHISK_HOT = "whisk_hot"
    REDUCE = "reduce"
    SAUTE_SIMMER = "saute_simmer"
    # Toppings
    CRUMBLE = "crumble"
    # Escape hatch
    CUSTOM = "custom"


# Allowed cooking methods per category (vision §Logic 1).
ALLOWED_METHODS: dict[Category, frozenset[CookingMethod]] = {
    Category.BASE: frozenset(
        {
            CookingMethod.BOIL,
            CookingMethod.STEAM,
            CookingMethod.BLANCH,
            CookingMethod.PAN_FRY,
            CookingMethod.ROAST,
            CookingMethod.AIR_FRY,
            CookingMethod.GRILL,
            CookingMethod.BAKE,
            CookingMethod.TOAST,
            CookingMethod.RAW,
            CookingMethod.NO_PREP,
            CookingMethod.CUSTOM,
        }
    ),
    Category.VEGETABLE: frozenset(
        {
            CookingMethod.BOIL,
            CookingMethod.STEAM,
            CookingMethod.BLANCH,
            CookingMethod.PAN_FRY,
            CookingMethod.ROAST,
            CookingMethod.AIR_FRY,
            CookingMethod.GRILL,
            CookingMethod.BAKE,
            CookingMethod.TOAST,
            CookingMethod.RAW,
            CookingMethod.NO_PREP,
            CookingMethod.CUSTOM,
        }
    ),
    Category.SAUCE: frozenset(
        {
            CookingMethod.BLEND_COLD,
            CookingMethod.BLEND_HOT,
            CookingMethod.HEAT,
            CookingMethod.WHISK_COLD,
            CookingMethod.WHISK_HOT,
            CookingMethod.REDUCE,
            CookingMethod.SAUTE_SIMMER,
            CookingMethod.NO_PREP,
            CookingMethod.CUSTOM,
        }
    ),
    Category.TOPPING: frozenset(
        {
            CookingMethod.BOIL,
            CookingMethod.TOAST,
            CookingMethod.PAN_FRY,
            CookingMethod.CRUMBLE,
            CookingMethod.NO_PREP,
            CookingMethod.CUSTOM,
        }
    ),
}


@dataclass(frozen=True, slots=True)
class Macros:
    """Macros per 100g of edible component."""

    kcal: float
    carbs_g: float
    protein_g: float
    fat_g: float
    fiber_g: float

    def __post_init__(self) -> None:
        for label, value in (
            ("kcal", self.kcal),
            ("carbs_g", self.carbs_g),
            ("protein_g", self.protein_g),
            ("fat_g", self.fat_g),
            ("fiber_g", self.fiber_g),
        ):
            if value < 0:
                raise ValueError(f"{label} must be >= 0, got {value}")


@dataclass(frozen=True, slots=True)
class Portion:
    value: float
    unit: PortionUnit

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError(f"portion value must be > 0, got {self.value}")


@dataclass(frozen=True, slots=True)
class CookingMethodSpec:
    """A cooking method this component supports, with method-specific notes."""

    method: CookingMethod
    approx_minutes: int | None = None
    can_cook_with_others: bool = True
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.approx_minutes is not None and self.approx_minutes < 0:
            raise ValueError("approx_minutes must be >= 0")


@dataclass(frozen=True, slots=True)
class Component:
    """The pure domain Component (vision §Data model)."""

    id: UUID
    category: Category
    name: str
    macros_per_100g: Macros
    default_portion: Portion
    default_cooking_method: CookingMethod
    cooking_methods: tuple[CookingMethodSpec, ...]
    flavor_tags: tuple[str, ...] = field(default_factory=tuple)
    dietary_tags: tuple[str, ...] = field(default_factory=tuple)
    allergens: tuple[str, ...] = field(default_factory=tuple)
    image_url: str | None = None
    shelf_life_days: int | None = None
    blacklisted: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        allowed = ALLOWED_METHODS[self.category]
        if self.default_cooking_method not in allowed:
            raise ValueError(
                f"default_cooking_method {self.default_cooking_method} "
                f"not allowed for category {self.category}"
            )
        if not self.cooking_methods:
            raise ValueError("cooking_methods must be non-empty")
        seen: set[CookingMethod] = set()
        for spec in self.cooking_methods:
            if spec.method in seen:
                raise ValueError(f"duplicate cooking method {spec.method}")
            seen.add(spec.method)
            if spec.method not in allowed:
                raise ValueError(
                    f"cooking method {spec.method} not allowed for category {self.category}"
                )
        if self.default_cooking_method not in seen:
            raise ValueError(
                "default_cooking_method must appear in cooking_methods"
            )
        if self.shelf_life_days is not None and self.shelf_life_days < 0:
            raise ValueError("shelf_life_days must be >= 0")


__all__ = [
    "ALLOWED_METHODS",
    "Category",
    "Component",
    "CookingMethod",
    "CookingMethodSpec",
    "Macros",
    "Portion",
    "PortionUnit",
]
