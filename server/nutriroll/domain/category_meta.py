"""Per-category metadata — single source of truth for slot configuration.

Framework-free: no FastAPI, no SQLAlchemy, no Pydantic. Both the roll
algorithm (`domain/roll.py`) and the meta API endpoint
(`api/routers/meta.py`) read from here so the enum, scoring targets, and
client-facing vocabulary cannot drift (modularity-audit M4 / M8).

Targets describe what a "balanced" component looks like per slot in
kcal / macro density per 100 g. They feed `_nutrition_fit()` and are
exposed verbatim by `GET /v1/meta/components` so clients can render the
same numbers used by the algorithm.

To tune targets without code changes, set
``NUTRIROLL_BALANCED_TARGETS_JSON`` in the environment. The expected
shape is ``{"<category>": {"<macro_key>": <float>, ...}, ...}``; partial
overrides are supported and merged on top of the defaults below.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, cast

from nutriroll.domain.component import Category

_DEFAULT_BALANCED_TARGETS: dict[Category, dict[str, float]] = {
    Category.BASE: {
        "kcal": 130.0,
        "carbs_g": 25.0,
        "protein_g": 4.0,
        "fat_g": 1.5,
        "fiber_g": 2.0,
    },
    Category.VEGETABLE: {
        "kcal": 35.0,
        "carbs_g": 7.0,
        "protein_g": 2.0,
        "fat_g": 0.4,
        "fiber_g": 2.5,
    },
    Category.SAUCE: {
        "kcal": 120.0,
        "carbs_g": 8.0,
        "protein_g": 2.0,
        "fat_g": 9.0,
        "fiber_g": 1.0,
    },
    Category.TOPPING: {
        "kcal": 200.0,
        "carbs_g": 10.0,
        "protein_g": 12.0,
        "fat_g": 12.0,
        "fiber_g": 4.0,
    },
}


def _load_overrides() -> dict[Category, dict[str, float]]:
    raw = os.environ.get("NUTRIROLL_BALANCED_TARGETS_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"NUTRIROLL_BALANCED_TARGETS_JSON is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("NUTRIROLL_BALANCED_TARGETS_JSON must be a JSON object")
    out: dict[Category, dict[str, float]] = {}
    parsed_typed = cast(dict[str, Any], parsed)
    for cat_key, macros in parsed_typed.items():
        category = Category(str(cat_key))
        if not isinstance(macros, dict):
            raise ValueError(f"NUTRIROLL_BALANCED_TARGETS_JSON[{cat_key!r}] must be an object")
        macros_typed = cast(dict[str, Any], macros)
        out[category] = {str(k): float(v) for k, v in macros_typed.items()}
    return out


def _build_targets() -> Mapping[Category, Mapping[str, float]]:
    overrides = _load_overrides()
    merged: dict[Category, dict[str, float]] = {}
    for category in Category:
        base = dict(_DEFAULT_BALANCED_TARGETS[category])
        base.update(overrides.get(category, {}))
        merged[category] = base
    # Make the result read-only so callers cannot mutate algorithm state.
    return MappingProxyType(
        {category: MappingProxyType(macros) for category, macros in merged.items()}
    )


BALANCED_TARGETS: Mapping[Category, Mapping[str, float]] = _build_targets()
"""Read-only per-category macro targets (kcal/100 g and macro grams/100 g)."""

# ---------------------------------------------------------------------------
# Pantry freshness
# ---------------------------------------------------------------------------

EXPIRY_WARNING_DAYS: int = int(os.environ.get("NUTRIROLL_EXPIRY_WARNING_DAYS", "3"))
"""Items expiring within this many days are considered "about to expire".

Used by:
- ``api/routers/roll.py`` — boosts pantry_bonus for expiring components.
- Exposed via ``GET /v1/meta/components`` so the frontend uses the same
  threshold without duplicating the constant (modularity-audit M9).

Override with the ``NUTRIROLL_EXPIRY_WARNING_DAYS`` environment variable.
"""


__all__ = ["BALANCED_TARGETS", "EXPIRY_WARNING_DAYS"]
