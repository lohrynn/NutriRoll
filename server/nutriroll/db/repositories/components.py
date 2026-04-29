"""Component repository — pure async data access. Returns domain objects."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.db.models.component import ComponentRow
from nutriroll.domain.component import (
    Category,
    Component,
    CookingMethod,
    CookingMethodSpec,
    Macros,
    Portion,
    PortionUnit,
)


class ComponentNameTakenError(Exception):
    """Raised when a component with the same name already exists."""


def _row_to_domain(row: ComponentRow) -> Component:
    methods = tuple(
        CookingMethodSpec(
            method=CookingMethod(spec["method"]),
            approx_minutes=spec.get("approx_minutes"),
            can_cook_with_others=bool(spec.get("can_cook_with_others", True)),
            notes=spec.get("notes"),
        )
        for spec in row.cooking_methods
    )
    return Component(
        id=row.id,
        category=Category(row.category),
        name=row.name,
        macros_per_100g=Macros.from_mapping(dict(row.macros)),
        default_portion=Portion(
            value=row.default_portion_value,
            unit=PortionUnit(row.default_portion_unit),
        ),
        default_cooking_method=CookingMethod(row.default_cooking_method),
        cooking_methods=methods,
        flavor_tags=tuple(row.flavor_tags),
        dietary_tags=tuple(row.dietary_tags),
        allergens=tuple(row.allergens),
        image_url=row.image_url,
        shelf_life_days=row.shelf_life_days,
        seasonal_availability=row.seasonal_availability,
        blacklisted=row.blacklisted,
    )


def _domain_to_columns(component: Component) -> dict[str, Any]:
    return {
        "id": component.id,
        "category": component.category.value,
        "name": component.name,
        "image_url": component.image_url,
        "default_portion_value": component.default_portion.value,
        "default_portion_unit": component.default_portion.unit.value,
        "macros": component.macros_per_100g.as_dict(),
        "default_cooking_method": component.default_cooking_method.value,
        "cooking_methods": [
            {
                "method": spec.method.value,
                "approx_minutes": spec.approx_minutes,
                "can_cook_with_others": spec.can_cook_with_others,
                "notes": spec.notes,
            }
            for spec in component.cooking_methods
        ],
        "flavor_tags": list(component.flavor_tags),
        "dietary_tags": list(component.dietary_tags),
        "allergens": list(component.allergens),
        "shelf_life_days": component.shelf_life_days,
        "seasonal_availability": component.seasonal_availability,
        "blacklisted": component.blacklisted,
    }


class ComponentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        category: Category | None = None,
        include_blacklisted: bool = True,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Component]:
        stmt = select(ComponentRow).order_by(ComponentRow.category, ComponentRow.name)
        if category is not None:
            stmt = stmt.where(ComponentRow.category == category.value)
        if not include_blacklisted:
            stmt = stmt.where(ComponentRow.blacklisted.is_(False))
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [_row_to_domain(row) for row in result.scalars().all()]

    async def get(self, component_id: UUID) -> Component | None:
        row = await self._session.get(ComponentRow, component_id)
        return _row_to_domain(row) if row is not None else None

    async def create(self, component: Component) -> Component:
        row = ComponentRow(**_domain_to_columns(component))
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ComponentNameTakenError(component.name) from exc
        await self._session.commit()
        await self._session.refresh(row)
        return _row_to_domain(row)

    async def update(self, component: Component) -> Component | None:
        row = await self._session.get(ComponentRow, component.id)
        if row is None:
            return None
        for key, value in _domain_to_columns(component).items():
            if key == "id":
                continue
            setattr(row, key, value)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ComponentNameTakenError(component.name) from exc
        await self._session.commit()
        await self._session.refresh(row)
        return _row_to_domain(row)

    async def delete(self, component_id: UUID) -> bool:
        row = await self._session.get(ComponentRow, component_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True


__all__ = ["ComponentNameTakenError", "ComponentRepository"]
