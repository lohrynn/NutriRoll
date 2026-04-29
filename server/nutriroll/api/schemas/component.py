"""Pydantic v2 schemas for the Component HTTP API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from nutriroll.domain.component import (
    ALLOWED_METHODS,
    Category,
    Component,
    CookingMethod,
    CookingMethodSpec,
    Macros,
    Portion,
    PortionUnit,
)

NonEmptyStr = Annotated[str, Field(min_length=1, max_length=200)]


class MacrosSchema(BaseModel):
    # ``extra="allow"`` lets clients send forward-compat macro fields
    # (e.g. ``sodium_mg``, ``sugar_g``) that are persisted into the JSONB
    # column without requiring a domain/ORM/migration round-trip. The five
    # well-known fields stay first-class for type-safe access.
    model_config = ConfigDict(extra="allow")

    kcal: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    fiber_g: float = Field(ge=0)

    def to_domain(self) -> Macros:
        extras: list[tuple[str, float]] = []
        for key, raw in (self.model_extra or {}).items():
            try:
                value = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"extra macro {key!r} must be numeric") from exc
            extras.append((key, value))
        return Macros(
            kcal=self.kcal,
            carbs_g=self.carbs_g,
            protein_g=self.protein_g,
            fat_g=self.fat_g,
            fiber_g=self.fiber_g,
            extra=tuple(extras),
        )

    @classmethod
    def from_domain(cls, m: Macros) -> MacrosSchema:
        return cls(
            kcal=m.kcal,
            carbs_g=m.carbs_g,
            protein_g=m.protein_g,
            fat_g=m.fat_g,
            fiber_g=m.fiber_g,
            **{key: value for key, value in m.extra},
        )


class PortionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float = Field(gt=0)
    unit: PortionUnit

    def to_domain(self) -> Portion:
        return Portion(value=self.value, unit=self.unit)

    @classmethod
    def from_domain(cls, p: Portion) -> PortionSchema:
        return cls(value=p.value, unit=p.unit)


class CookingMethodSpecSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: CookingMethod
    approx_minutes: int | None = Field(default=None, ge=0)
    can_cook_with_others: bool = True
    notes: str | None = Field(default=None, max_length=500)

    def to_domain(self) -> CookingMethodSpec:
        return CookingMethodSpec(
            method=self.method,
            approx_minutes=self.approx_minutes,
            can_cook_with_others=self.can_cook_with_others,
            notes=self.notes,
        )

    @classmethod
    def from_domain(cls, s: CookingMethodSpec) -> CookingMethodSpecSchema:
        return cls(
            method=s.method,
            approx_minutes=s.approx_minutes,
            can_cook_with_others=s.can_cook_with_others,
            notes=s.notes,
        )


class ComponentBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    name: NonEmptyStr
    image_url: str | None = Field(default=None, max_length=2048)
    macros_per_100g: MacrosSchema
    default_portion: PortionSchema
    default_cooking_method: CookingMethod
    cooking_methods: list[CookingMethodSpecSchema] = Field(min_length=1)
    flavor_tags: list[NonEmptyStr] = Field(default_factory=list, max_length=32)
    dietary_tags: list[NonEmptyStr] = Field(default_factory=list, max_length=32)
    allergens: list[NonEmptyStr] = Field(default_factory=list, max_length=32)
    shelf_life_days: int | None = Field(default=None, ge=0)
    seasonal_availability: str | None = Field(default=None, min_length=1, max_length=64)
    blacklisted: bool = False

    @field_validator("flavor_tags", "dietary_tags", "allergens")
    @classmethod
    def _no_duplicate_tags(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("tags must be unique")
        return v

    @model_validator(mode="after")
    def _validate_methods(self) -> ComponentBase:
        allowed = ALLOWED_METHODS[self.category]
        if self.default_cooking_method not in allowed:
            raise ValueError(
                f"default_cooking_method '{self.default_cooking_method.value}' "
                f"not allowed for category '{self.category.value}'"
            )
        seen: set[CookingMethod] = set()
        for spec in self.cooking_methods:
            if spec.method in seen:
                raise ValueError(f"duplicate cooking method '{spec.method.value}'")
            seen.add(spec.method)
            if spec.method not in allowed:
                raise ValueError(
                    f"cooking method '{spec.method.value}' "
                    f"not allowed for category '{self.category.value}'"
                )
        if self.default_cooking_method not in seen:
            raise ValueError("default_cooking_method must appear in cooking_methods")
        return self


class ComponentCreate(ComponentBase):
    pass


class ComponentRead(ComponentBase):
    id: UUID

    @classmethod
    def from_domain(cls, c: Component) -> ComponentRead:
        return cls(
            id=c.id,
            category=c.category,
            name=c.name,
            image_url=c.image_url,
            macros_per_100g=MacrosSchema.from_domain(c.macros_per_100g),
            default_portion=PortionSchema.from_domain(c.default_portion),
            default_cooking_method=c.default_cooking_method,
            cooking_methods=[CookingMethodSpecSchema.from_domain(s) for s in c.cooking_methods],
            flavor_tags=list(c.flavor_tags),
            dietary_tags=list(c.dietary_tags),
            allergens=list(c.allergens),
            shelf_life_days=c.shelf_life_days,
            seasonal_availability=c.seasonal_availability,
            blacklisted=c.blacklisted,
        )


class ComponentList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ComponentRead]
    total: int


__all__ = [
    "ComponentBase",
    "ComponentCreate",
    "ComponentList",
    "ComponentRead",
    "CookingMethodSpecSchema",
    "MacrosSchema",
    "PortionSchema",
]
