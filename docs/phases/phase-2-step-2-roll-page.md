# Phase 2 Step 2 — Roll-a-bowl Page

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 40/40 ✓ vitest 9/9 ✓

---

## What was built

Frontend `/roll` page that talks to the Phase 2 Step 1 endpoints. Lets the user set constraints (time budget, dietary mode, allergens), roll a 4-slot bowl (base + vegetable + sauce + topping), see per-slot reasons, and reroll any individual slot. All strings via next-intl (en + de).

## Files created

| Path | Purpose |
|---|---|
| `web/lib/roll/types.ts` | Re-exports `RollRequest`/`RolledBowl`/`RolledSlot`/`SlotSpec` from the generated OpenAPI schema; defines `DEFAULT_SLOTS` (one of each category). |
| `web/components/roll-page.tsx` | Client component. Constraint form (time budget, dietary mode, allergens CSV). "Roll a bowl" button → `POST /v1/roll`. Per-slot "Reroll" button → `POST /v1/roll/slot`, splices the returned slot into the local bowl. `<output aria-live>` for errors. |
| `web/app/roll/page.tsx` | RSC route at `/roll`. Wraps `<RollPage />`. |
| `web/tests/unit/roll-page.test.tsx` | 3 vitest tests: rolls a bowl + renders reasons + checks request body; surfaces error from 422; reroll updates a single slot via the slot endpoint. |

## Files modified

| Path | Change |
|---|---|
| `web/messages/en.json` | New `roll.*` namespace + `nav.roll`. |
| `web/messages/de.json` | German equivalents. |

## Key technical decisions

| Decision | Reason |
|---|---|
| Stateless reroll splicing client-side | Mirrors the API design (Step 1). The client knows its current bowl; reroll just needs the constraints + which category + which ids to exclude. No server-side session. |
| `temperature: 0.5` sent explicitly from the client | OpenAPI generated schema marks it required despite the Pydantic default; sending it explicitly is simpler than working around the type. |
| `<output aria-live="polite">` for errors | Same biome `useSemanticElements` invariant as the components page — `<div role="status">` is rejected. |
| One test file per page | Keeps test surface focused; mirrors the component-manager pattern. |

## Invariants added

- The `forced_methods` field on the wire is a `Record<Category, CookingMethod>` (i.e. one forced method per slot category at most). Sparse map; missing keys mean "no constraint".
- The reroll endpoint is the only way to bias a single slot — the algorithm does not expose partial-fix semantics directly.

## What's next (Phase 3)

- **Cooking Recipe View** (vision MVP §3): given a `RolledBowl`, render the parallel cooking blocks + timers per `cooking_methods[*].approx_minutes`.
