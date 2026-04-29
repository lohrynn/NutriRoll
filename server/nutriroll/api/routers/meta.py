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
from nutriroll.domain.equipment import DEFAULT_EQUIPMENT, METHOD_REQUIREMENTS, Equipment

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
    equipment: list[Equipment]
    """Phase 13. Vocabulary of equipment chips the Settings page renders."""
    method_requirements: dict[CookingMethod, list[Equipment]]
    """Phase 13. Per-method equipment requirements; the frontend uses this to
    decide which icons to show on a bowl card and to keep the Settings UI in
    sync with the algorithm's hard-filter rules (modularity-audit pattern)."""
    default_equipment: list[Equipment]
    """Phase 13. Sensible defaults for new users (oven + stovetop + microwave)."""
    llm_configured: bool
    """Whether prompt-based component generation is available on this server."""


@router.get(
    "/components",
    response_model=ComponentMeta,
    summary="Component vocabulary (categories, portion units, allowed methods, balanced targets)",
)
async def get_component_meta() -> ComponentMeta:
    from nutriroll.config import get_settings

    settings = get_settings()
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
        equipment=list(Equipment),
        method_requirements={
            method: sorted(METHOD_REQUIREMENTS.get(method, frozenset()), key=lambda e: e.value)
            for method in CookingMethod
        },
        default_equipment=sorted(DEFAULT_EQUIPMENT, key=lambda e: e.value),
        llm_configured=bool(settings.openai_api_key.strip()),
    )
