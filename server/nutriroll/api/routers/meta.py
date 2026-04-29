"""Static metadata endpoints — single source of truth for client constants.

These endpoints expose enums/relations that previously had to be hand-mirrored
in the TypeScript frontend (see `docs/modularity-audit.md` M4/M5). The
TypeScript client is regenerated via `make gen-client`, and the frontend
fetches these values at runtime instead of duplicating them.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from nutriroll.domain.category_meta import BALANCED_TARGETS, EXPIRY_WARNING_DAYS
from nutriroll.domain.component import (
    ALLOWED_METHODS,
    Category,
    CookingMethod,
    PortionUnit,
)

router = APIRouter(prefix="/v1/meta", tags=["meta"])


class ComponentMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categories: list[Category]
    portion_units: list[PortionUnit]
    allowed_methods: dict[Category, list[CookingMethod]]
    balanced_targets: dict[Category, dict[str, float]]
    expiry_warning_days: int
    """Number of days before expiry at which a pantry item is considered
    "about to expire". Used by the roll algorithm and pantry UI.
    Set via ``NUTRIROLL_EXPIRY_WARNING_DAYS`` env var (default: 3)."""
    category_labels: dict[Category, str]
    """Human-readable English display names for each category, derived from
    the enum. Used by the frontend as i18n fallbacks so unknown categories
    (e.g. a newly-added slot type) are still rendered meaningfully without
    a code change to the translation files (modularity-audit M4)."""


@router.get(
    "/components",
    response_model=ComponentMeta,
    summary="Component vocabulary (categories, portion units, allowed methods, balanced targets)",
)
async def get_component_meta() -> ComponentMeta:
    return ComponentMeta(
        categories=list(Category),
        portion_units=list(PortionUnit),
        allowed_methods={
            category: sorted(methods, key=lambda m: m.value)
            for category, methods in ALLOWED_METHODS.items()
        },
        balanced_targets={
            category: dict(targets) for category, targets in BALANCED_TARGETS.items()
        },
        expiry_warning_days=EXPIRY_WARNING_DAYS,
        category_labels={
            category: category.value.replace("_", " ").title() for category in Category
        },
    )
