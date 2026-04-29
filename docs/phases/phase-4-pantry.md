# Phase 4 — Pantry

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 73/73 ✓ vitest 12/12 ✓

---

## What was built

End-to-end pantry: track on-hand quantities of components, optionally with `opened_at` and `expires_at` markers. Used later by the Shopping List builder to subtract from purchase needs.

## Backend

| Path | Purpose |
|---|---|
| `server/nutriroll/domain/pantry.py` | Frozen `PantryItem` dataclass with quantity/unit/opened/expires fields. |
| `server/nutriroll/db/models/pantry.py` | `PantryItemRow` (UUID PK, FK→component, quantity Numeric, unit, opened_at, expires_at). |
| `server/nutriroll/db/repositories/pantry.py` | Async CRUD: `list_items`, `create`, `update`, `delete`. |
| `server/nutriroll/api/schemas/pantry.py` | Pydantic v2 `PantryItemRead/Create/Update` with `extra="forbid"` and `to_domain`/`from_domain`. |
| `server/nutriroll/api/routers/pantry.py` | `GET/POST/PUT/DELETE /v1/pantry`. Translates missing-component FK to 404 `{code:"component_not_found"}`. |
| `server/alembic/versions/0002_pantry_stores_history.py` | Postgres DDL for the new tables (Phase 4 + 5 + 6 batched). |
| `server/tests/test_pantry_api.py` | 5 tests: list, create, update, delete, FK miss. |

## Frontend

| Path | Purpose |
|---|---|
| `web/lib/pantry/types.ts` | Re-exports schema types. |
| `web/components/pantry-page.tsx` | "use client". Loads `/v1/pantry` + `/v1/components` in parallel, list with brand-soft chip + brand badge for `{value} {unit}` + opened/expires badges + delete. Add form: component select, quantity+unit grid, expires date input, opened checkbox. |
| `web/app/pantry/page.tsx` | RSC route wrapped in `PageShell`. |

## Key decisions

- **Quantity model** mirrors `Portion` from the recipe domain (`PortionUnit.GRAM/MILLILITER/PIECE`) so subtraction in shopping is a 1:1 unit match — mismatched units are simply ignored at shopping time.
- **No depletion tracking** — pantry quantity is updated explicitly via PUT. The shopping list does not mutate it.

## Invariants

- `quantity > 0` validated at the domain boundary.
- `expires_at >= opened_at` is *not* enforced (real life is messier than that).
