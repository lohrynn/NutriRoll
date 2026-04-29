# Phase 8 — Saved + Planned meals

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 88/88 ✓ vitest 12/12 ✓

---

## What was built

Vision §2 / §10 / §11: a place to save bowls you love and a week-by-week meal planner. Snapshots are stored as JSON so future component edits never retroactively rewrite history.

## Backend

| Path | Purpose |
|---|---|
| `server/nutriroll/domain/planning.py` | `SavedMeal`, `PlannedMeal`, `MealSlot` (breakfast/lunch/dinner/snack), `PlannedStatus` (planned/shopped/cooked/skipped). |
| `server/nutriroll/db/models/planning.py` | `SavedMealRow`, `PlannedMealRow` (JSON snapshot column, indexed `created_at`/`planned_for`). |
| `server/nutriroll/db/repositories/planning.py` | CRUD + range-query (`start`, `end`) for planned meals; `update()` supports moving day, changing slot, restatusing, editing notes. |
| `server/nutriroll/api/schemas/planning.py` | Pydantic schemas with `extra="forbid"`; `SavedMealCreate.name` rejects blank-after-strip via `field_validator`. |
| `server/nutriroll/api/routers/planning.py` | `saved_router` (`GET/POST/DELETE /v1/saved`) + `planned_router` (`GET/POST/PATCH/DELETE /v1/planned?start=&end=`). |
| `server/alembic/versions/0003_planning.py` | Postgres migration: `saved_meals`, `planned_meals` tables with JSONB snapshots and the indexes used by the range query. |
| `server/tests/test_planning_api.py` | 4 tests: saved CRUD, blank-name rejection (422), planned CRUD + range filter + PATCH move/cooked, unknown slot rejection. |

## Frontend

| Path | Purpose |
|---|---|
| `web/lib/planning/types.ts` | Re-exports of openapi types + `MEAL_SLOTS` / `PLANNED_STATUSES` constants. |
| `web/components/saved-page.tsx` | Lists saved bowls with preview line, delete, and one-tap "Cook" (loads bowl into session storage and routes to `/recipe`). |
| `web/components/plan-page.tsx` | Mon-based week view with prev/next navigation. Per-day card lists planned meals as chips (slot + status badges). Actions: Cook (handoff to `/recipe`), toggle cooked/planned, delete. Uses URL-style date strings (`YYYY-MM-DD`). |
| `web/app/saved/page.tsx`, `web/app/plan/page.tsx` | Route shells with `PageShell`. |
| `web/components/roll-page.tsx` | New "Save" + "Plan today" buttons next to "Cook now" on the bowl card. Save prompts for a name; Plan today schedules the current bowl for `dinner` and routes to `/plan`. |
| `web/components/bottom-nav.tsx` | "Plan" tab now points to `/plan`; matches `/plan`, `/saved`, `/history`. |
| `web/app/me/page.tsx` | Added Saved + History tiles. |
| `web/messages/{en,de}.json` | Full `saved.*` and `plan.*` namespaces; `roll.saveBowl`, `roll.planToday`, `roll.savePrompt`. |

## Key decisions

- **Snapshots, not references.** Bowls are JSON-frozen at save/plan time so editing or deleting components later doesn't corrupt the user's history. This matches the append-only spirit of the existing history feed.
- **Blank-name rejection at the schema layer**, not the domain layer, so the API responds with 422 (validation) instead of letting `ValueError` bubble to a 500. The domain dataclass keeps its invariant as a defense in depth.
- **Mon-based weeks** in the planner — matches European convention and aligns with the German locale. The `startOfWeek` helper computes `(day + 6) % 7` shift to land on Monday.
- **`Plan today` defaults to dinner**. The week view supports moving the meal afterwards via PATCH; choosing a slot at roll time would require a date+slot picker that adds friction to the happy path.
- **No `cookie` / `header` `path` fields are queried** — every endpoint is `parameters: { query?: never }` style except where genuinely needed (range filter, path id).

## Invariants

- Saved meal rows survive component CRUD (FK-less JSON snapshot).
- Range query `start`/`end` are inclusive on both ends.
- PATCH with omitted fields leaves the corresponding columns untouched (None means "no change").
- Status transitions are unrestricted server-side; the UI only exposes the cooked ⇄ planned toggle today, but `shopped` and `skipped` are reserved for future flows (shopping handoff, leftover/discard).
