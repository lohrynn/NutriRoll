# Phase 3 Step 2 — `/recipe` Page + "Cook now" Handoff

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 52/52 ✓ vitest 12/12 ✓

---

## What was built

Frontend `/recipe` page that consumes the `POST /v1/recipe` endpoint
from Step 1. The user reaches it from the Roll page via a new "Cook
now" button: the rolled bowl is stashed in `sessionStorage` and the
recipe page picks it up on mount, calls the API, and renders the
parallel cooking blocks with per-step instructions and offsets.

## Files created

| Path | Purpose |
|---|---|
| `web/lib/recipe/types.ts` | Re-exports `Recipe`, `RecipeBlock`, `RecipeStep`, `BuildRecipeRequest` from the generated OpenAPI schema. |
| `web/lib/recipe/storage.ts` | Single source of truth for the `sessionStorage` key (`ROLLED_BOWL_STORAGE_KEY = "nutriroll.rolledBowl"`) shared between Roll page and Recipe page. |
| `web/components/recipe-page.tsx` | "use client". Reads the bowl from `sessionStorage` on mount; if missing, shows a "no bowl found" message linking back to `/roll`. Otherwise calls `POST /v1/recipe` with the slot component ids and renders blocks (title, category, method, total minutes, steps). |
| `web/app/recipe/page.tsx` | RSC route at `/recipe`. Wraps `<RecipePage />` in a back-link layout. |
| `web/tests/unit/recipe-page.test.tsx` | 3 vitest tests: missing-bowl message; success path verifies request body + rendered block; 422 surfaces error code in `<output role="status">`. |

## Files modified

| Path | Change |
|---|---|
| `web/components/roll-page.tsx` | Added "Cook now" button next to the "Your bowl" heading. On click: stores `JSON.stringify(bowl)` in `sessionStorage` under the shared key and `router.push("/recipe")`. Imports `useRouter` from `next/navigation`. |
| `web/messages/en.json` + `web/messages/de.json` | Added `nav.recipe`, `roll.cookNow`, full `recipe.*` namespace. |
| `web/tests/unit/roll-page.test.tsx` | Added `vi.mock("next/navigation", …)` so `useRouter()` works in jsdom. |

## Key technical decisions

| Decision | Reason |
|---|---|
| Bowl handoff via `sessionStorage`, not URL params or server state | The bowl payload is large (full component objects with macros + cooking methods). URL would balloon and leak via referers; server-side session adds infra for no benefit. `sessionStorage` is exactly the right scope: same tab, cleared on close. |
| Single shared storage-key constant in `lib/recipe/storage.ts` | Prevents the producer (Roll page) and consumer (Recipe page) from drifting on the magic string. |
| Recipe page calls `POST /v1/recipe` itself, on mount | The server is the source of truth for the recipe. The bowl carries components; the recipe is derived. Having the page rebuild on mount also means re-mounting (e.g. via back/forward) re-derives instead of caching stale steps. |
| Three discriminated `Status` cases (`loading` / `building` / `ok` / `missing` / `error`) | Same pattern as Roll page; keeps the JSX flat with one `<output>` per terminal state. |
| `<output aria-live="polite">` for status messages | Matches the biome `useSemanticElements` invariant adopted in Phase 1/2 (no `<div role="status">`). |

## Invariants added

- The Roll page is the only producer of `nutriroll.rolledBowl` in `sessionStorage`. Anyone else reading or writing this key is a bug.
- The Recipe page never inspects `score` or `reasons` — those live on the rolled bowl but are intentionally absent from `Recipe`.

## What's next

Phase 3 closes out the MVP cooking flow. Logical next phases per
`PROJECT_VISION.md`: Pantry/Inventory (§4), Shopping List (§5), or
Rate-a-Meal (§3).
