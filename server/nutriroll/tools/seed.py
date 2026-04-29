"""Seed loader — reads CSVs and idempotently upserts components into the DB.

Usage::

    uv run python -m nutriroll.tools.seed \\
        --components ../data/seed/components.csv \\
        --methods    ../data/seed/cooking_methods.csv

Without ``--force`` the loader refuses to run against a non-empty database.
With ``--force`` it skips rows whose ``name`` already exists (idempotent).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from nutriroll.db.models.component import ComponentRow
from nutriroll.db.repositories.components import ComponentNameTakenError, ComponentRepository
from nutriroll.db.session import get_sessionmaker
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

# Some seed rows use ``sauté`` (with accent) for vegetables — that label is
# not in the controlled vocabulary; vision §Logic 1 lists ``Pan-fry`` as the
# closest vegetable method. Mapping is intentionally narrow.
_METHOD_ALIASES: dict[str, CookingMethod] = {
    "saute": CookingMethod.PAN_FRY,
    "sauté": CookingMethod.PAN_FRY,
}


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "y", "t"}


def _parse_method(raw: str) -> CookingMethod:
    key = raw.strip().lower()
    if key in _METHOD_ALIASES:
        return _METHOD_ALIASES[key]
    return CookingMethod(key)


def _parse_pipe_list(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split("|") if part.strip())


def _read_methods(path: Path) -> dict[int, list[CookingMethodSpec]]:
    grouped: dict[int, list[CookingMethodSpec]] = defaultdict(list)
    seen: dict[int, set[CookingMethod]] = defaultdict(set)
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            comp_id = int(row["component_id"])
            method = _parse_method(row["method"])
            if method in seen[comp_id]:
                continue
            seen[comp_id].add(method)
            minutes_raw = row["approx_cook_min"].strip()
            spec = CookingMethodSpec(
                method=method,
                approx_minutes=int(minutes_raw) if minutes_raw else None,
                can_cook_with_others=_parse_bool(row["can_cook_with_others"]),
                notes=(row.get("notes") or "").strip() or None,
            )
            grouped[comp_id].append(spec)
    return grouped


def _build_component(
    row: dict[str, str],
    methods: list[CookingMethodSpec],
) -> Component:
    category = Category(row["category"].strip().lower())
    allowed = ALLOWED_METHODS[category]

    # Filter to allowed methods only (drops e.g. ``no_prep`` that may appear
    # in seed but isn't relevant for a category — currently a no-op).
    filtered = [spec for spec in methods if spec.method in allowed]
    if not filtered:
        raise ValueError(
            f"component {row['name']!r} has no cooking methods that are "
            f"valid for its category {category.value}"
        )

    default_method = _parse_method(row["default_cooking_method"])
    if default_method not in allowed:
        raise ValueError(
            f"component {row['name']!r}: default method {default_method} "
            f"not allowed for category {category.value}"
        )
    if default_method not in {spec.method for spec in filtered}:
        # Inject the default method as an extra spec so the Component
        # invariant holds. Use no time / can-cook flag from the closest spec.
        filtered.append(
            CookingMethodSpec(
                method=default_method,
                approx_minutes=None,
                can_cook_with_others=True,
                notes=None,
            )
        )

    return Component(
        id=uuid4(),
        category=category,
        name=row["name"].strip(),
        macros_per_100g=Macros(
            kcal=float(row["kcal_per_100g"]),
            carbs_g=float(row["carbs_per_100g"]),
            protein_g=float(row["protein_per_100g"]),
            fat_g=float(row["fat_per_100g"]),
            fiber_g=float(row["fiber_per_100g"]),
        ),
        default_portion=Portion(
            value=float(row["default_portion_value"]),
            unit=PortionUnit(row["default_portion_unit"].strip().lower()),
        ),
        default_cooking_method=default_method,
        cooking_methods=tuple(filtered),
        flavor_tags=_parse_pipe_list(row.get("flavor_tags", "")),
        dietary_tags=_parse_pipe_list(row.get("dietary_tags", "")),
        allergens=_parse_pipe_list(row.get("allergens", "")),
        shelf_life_days=int(row["shelf_life_days"]) if row.get("shelf_life_days") else None,
        seasonal_availability=(row.get("typical_availability") or "").strip() or None,
        blacklisted=_parse_bool(row.get("blacklisted", "false")),
    )


def read_seed(
    components_path: Path,
    methods_path: Path,
) -> list[Component]:
    """Parse CSVs into validated `Component` instances."""
    methods_by_id = _read_methods(methods_path)
    components: list[Component] = []
    with components_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            comp_id = int(row["id"])
            method_specs = methods_by_id.get(comp_id, [])
            if not method_specs:
                raise ValueError(
                    f"component {row['name']!r} (id={comp_id}) has no rows in cooking_methods.csv"
                )
            components.append(_build_component(row, list(method_specs)))
    return components


async def upsert_components(
    components: Iterable[Component],
    *,
    force: bool,
) -> tuple[int, int]:
    """Insert components by name. Returns ``(inserted, skipped)``.

    Refuses to run against a non-empty database without ``force=True``.
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        existing_count = (await session.execute(select(ComponentRow.id).limit(1))).scalar()
        if existing_count is not None and not force:
            raise RuntimeError(
                "database already contains components — pass --force to "
                "skip-on-name-collision idempotent upsert"
            )

        existing_names = {
            name for (name,) in (await session.execute(select(ComponentRow.name))).all()
        }
        repo = ComponentRepository(session)
        inserted = 0
        skipped = 0
        for component in components:
            if component.name in existing_names:
                skipped += 1
                continue
            try:
                await repo.create(component)
                inserted += 1
            except ComponentNameTakenError:
                skipped += 1
        return inserted, skipped


def _resolve_default(arg: str | None, fallback: Path) -> Path:
    return Path(arg) if arg else fallback


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NutriRoll seed loader")
    repo_root = Path(__file__).resolve().parents[3]
    parser.add_argument("--components", default=None)
    parser.add_argument("--methods", default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow running against a non-empty database (idempotent upsert).",
    )
    args = parser.parse_args(argv)

    components_path = _resolve_default(
        args.components, repo_root / "data" / "seed" / "components.csv"
    )
    methods_path = _resolve_default(
        args.methods, repo_root / "data" / "seed" / "cooking_methods.csv"
    )

    components = read_seed(components_path, methods_path)
    sys.stderr.write(f"parsed {len(components)} components from CSV\n")

    try:
        inserted, skipped = asyncio.run(upsert_components(components, force=args.force))
    except RuntimeError as err:
        sys.stderr.write(f"error: {err}\n")
        return 2
    sys.stderr.write(f"inserted={inserted} skipped={skipped}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
