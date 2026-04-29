# Phase 5 — Stores + Shopping List

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 73/73 ✓ vitest 12/12 ✓

---

## What was built

Two layers wired together:

1. **Stores + per-store prices** — manage supermarkets and the price/pack-size of each component at each store. One store can be marked primary.
2. **Shopping list builder** — given a rolled bowl + portion count + (optional) store, subtract pantry on-hand and return per-component `{quantity_to_buy, packs_to_buy, line_price}` plus a rounded total.

## Backend

| Path | Purpose |
|---|---|
| `server/nutriroll/domain/store.py` | `Store`, `SupermarketPrice` dataclasses. |
| `server/nutriroll/domain/shopping.py` | `aggregate_demand_for_bowl(components, portions)` and `build_shopping_list(demands, *, portions, prices, pantry)` — pure functions, no I/O. Pantry subtracted only when units match. `packs = ceil(to_buy/pack_size)`. Total rounded to 2dp. `has_missing_prices` flag exposed. |
| `server/nutriroll/db/models/store.py` | `StoreRow` (unique name), `SupermarketPriceRow` with `UniqueConstraint(store_id, component_id)`. |
| `server/nutriroll/db/repositories/stores.py` | Async CRUD; `create_store/update_store` clear prior `is_primary`; `delete_store` cascades prices; `upsert_price` enforces one row per (store, component). |
| `server/nutriroll/api/schemas/store.py` | `extra="forbid"`, `from_domain` converters. |
| `server/nutriroll/api/schemas/shopping.py` | `BuildShoppingListRequest {component_ids min_length=1, portions 1..20, store_id?, use_pantry=True}` and the response shape. |
| `server/nutriroll/api/routers/stores.py` | `/v1/stores` CRUD plus nested `/v1/stores/{id}/prices` GET/PUT(upsert)/DELETE. `IntegrityError` → 409 `store_name_taken`. |
| `server/nutriroll/api/routers/shopping.py` | `POST /v1/shopping-list`. Loads components, prices for the chosen store, pantry items, then calls the pure builder. |
| `server/tests/test_shopping_domain.py`, `test_shopping_api.py`, `test_stores_api.py` | 12 tests covering pricing, pack rounding, pantry subtraction, missing prices, primary-toggle invariants. |

## Frontend

| Path | Purpose |
|---|---|
| `web/lib/stores/types.ts`, `web/lib/shopping/types.ts` | Re-exports schema types. |
| `web/components/stores-page.tsx` | Per-store Card with Store icon chip + primary Star badge + delete (with `window.confirm`), nested prices list with badges, inline upsert form per store, bottom add-store form. |
| `web/components/shop-page.tsx` | Reads `RolledBowl` from `sessionStorage` (key shared with Recipe page), loads `/v1/stores` and auto-selects primary, posts `/v1/shopping-list` with `use_pantry:true`, renders total + per-portion badge + per-item rows (priced badge or warning badge for missing price). Empty state when no bowl: Link to `/roll`. |
| `web/app/stores/page.tsx`, `web/app/shop/page.tsx` | RSC routes wrapped in `PageShell`. |

## Key decisions

- **Stateless shopping endpoint.** No persisted "shopping list" entity — the list is computed fresh from `(bowl, portions, store_id)`. This keeps the data model tight and the UI free to recompute on every change.
- **Pantry subtraction only when units match.** Mixing grams/ml/pieces is too ambiguous to silently convert; mismatched units are passed through unchanged.
- **One price per (store, component).** Enforced by a DB unique constraint and the upsert path; updates replace the row in place.
- **Primary store** is a soft singleton: setting one clears others in a single transaction.

## Invariants

- `portions ∈ [1, 20]`, `component_ids` non-empty.
- `total_price` is the sum of `line_price`s, rounded to 2dp; `has_missing_prices=true` whenever any component has no price row at the chosen store.
- Deleting a store cascades to its prices but leaves pantry/components intact.
