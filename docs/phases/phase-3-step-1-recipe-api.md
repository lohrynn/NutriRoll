# Phase 3 Step 1 — Recipe Builder + `/v1/recipe` Endpoint

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 52/52 ✓ vitest 12/12 ✓

---

## What was built

Pure-function recipe builder that turns the chosen components of a rolled
bowl into a structured Recipe of parallel cooking blocks (vision §6
Cooking Recipe View). One HTTP entry point, `POST /v1/recipe`, takes the
ids of the chosen components and returns blocks sorted longest-first so
everything finishes together.

## Files created

| Path | Purpose |
|---|---|
| `server/nutriroll/domain/recipe.py` | `Recipe`, `RecipeBlock`, `RecipeStep` dataclasses + `build_recipe(components, forced_methods?) -> Recipe`. Vegetables that share a method and all `can_cook_with_others` are merged into one block with cumulative `offset_min`. Blocks are sorted by `total_minutes` descending. |
| `server/nutriroll/api/schemas/recipe.py` | Pydantic v2 schemas: `RecipeStepSchema`, `RecipeBlockSchema`, `RecipeSchema` (all with `from_domain()`), and `BuildRecipeRequestSchema { component_ids, forced_methods }`. |
| `server/nutriroll/api/routers/recipe.py` | `POST /v1/recipe`. Loads each requested component by id (404 if missing) and runs `build_recipe`. `IncompatibleForcedMethodError` → 422 `{code: incompatible_forced_method, component_id, method}`. |
| `server/tests/test_recipe_domain.py` | 7 pure tests: ordering, vegetable grouping, no grouping when methods differ, forced-method incompatible raises, forced-method used when compatible, empty input rejected, single-component block. |
| `server/tests/test_recipe_api.py` | 5 HTTP tests: ordering, grouping, 404 on unknown id, 422 on incompatible forced method, validation. |

## Files modified

| Path | Change |
|---|---|
| `server/nutriroll/api/app.py` | Mount `recipe.router`. |
| `web/lib/api/openapi.json` + `web/lib/api/schema.d.ts` | Regenerated. |

## Key technical decisions

| Decision | Reason |
|---|---|
| Recipe operates on `list[Component]`, not `RolledBowl` | Scores and reasons are roll-time concepts; the recipe doesn't need them. Keeping the domain narrow makes the builder reusable (e.g. for a "cook this saved bowl" path later). |
| Server reloads components by id (not full bowl payload) | Pool is small; round-tripping the full bowl JSON would couple the recipe API to the bowl wire format. ids are the natural primary key. |
| Vegetables grouped only when method **and** `can_cook_with_others` match | Mirrors vision §6: "If vegetables can be cooked in the same item, list all time steps when to add every vegetable in one vegetable cooking block." |
| `offset_min` per step, with the slowest item anchoring offset 0 | Lets the UI render a timeline; matches the cookbook convention "start the longest thing first". |
| `IncompatibleForcedMethodError` is the only domain exception translated to 422 | Same convention as Phase 2 — domain raises typed exceptions, the router maps them to structured 422 detail. Anything unexpected is a 500. |

## Invariants added

- `build_recipe([])` raises `ValueError`. The HTTP layer surfaces this as a 422 via Pydantic's `min_length=1`.
- A `RecipeBlock` always has at least one component and at least one step.
- `Recipe.total_minutes == max(block.total_minutes)` — assumes blocks cook in parallel, which holds for the v1 cooking model.
