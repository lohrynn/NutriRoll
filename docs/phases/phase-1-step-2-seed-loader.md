# Phase 1 Step 2 — Seed Loader

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 22/22 ✓ vitest 6/6 ✓

---

## What was built

A CLI loader that reads `data/seed/components.csv` + `data/seed/cooking_methods.csv`, builds validated `Component` domain objects, and idempotently upserts them into the database. Refuses to clobber a non-empty production DB without `--force`.

## Files created

| Path | Purpose |
|---|---|
| `server/nutriroll/tools/seed.py` | Main loader. `read_seed(...)` parses both CSVs and returns a `list[Component]`. `upsert_components(...)` is async, uses `get_sessionmaker()`, refuses non-empty DB without `--force`, otherwise inserts skipping by existing names. CLI entry: `python -m nutriroll.tools.seed --components <path> --methods <path> [--force]`. |
| `server/tests/test_seed_loader.py` | 5 tests: parses all CSV rows + 4 categories present; `sauté` alias maps to `pan_fry`; upsert into empty DB; refuses non-empty without `--force`; idempotent with `--force` (second call: 0 inserted, N skipped). |

## Files modified

| Path | Change |
|---|---|
| `tools/seed/load.py` | Stub now prints redirect: `cd server && uv run python -m nutriroll.tools.seed`. |
| `server/nutriroll/domain/component.py` | `ALLOWED_METHODS[Category.TOPPING]` extended with `ROAST` and `GRILL` (proteins-as-toppings: grilled chicken, halloumi, baked tofu, crispy chickpeas, tempeh). |
| `web/lib/components/types.ts` | Mirror updated for the same topping methods. |

## Key technical decisions

| Decision | Reason |
|---|---|
| `_METHOD_ALIASES = {"saute": PAN_FRY, "sauté": PAN_FRY}` | The seed CSV uses `sauté` (a real culinary technique not in the strict enum). Aliasing in the loader avoids polluting the domain enum with culinary synonyms. |
| Fresh `uuid4()` per row | The seed file uses int IDs for human readability; the DB uses UUIDs. Names are unique, so the upsert dedupes by name. |
| Extended topping methods (`ROAST`, `GRILL`) | The curated seed includes protein toppings that need `grill`/`roast` — real bowl ergonomics. The vision text was tightened in Step 1; the seed is the curated ground truth. No existing test asserted these methods were forbidden for toppings. |
| `--force` required for non-empty DB | Avoids accidental seed runs in production wiping or duplicating real data. |

## Invariants added

- `data/seed/components.csv` is the canonical seed — keep all its category/method combinations valid against `ALLOWED_METHODS`.
- The frontend `ALLOWED_METHODS` mirror in `web/lib/components/types.ts` must stay in sync with the Python `ALLOWED_METHODS` dict.
- Loader never inserts rows with names that already exist in the DB.
