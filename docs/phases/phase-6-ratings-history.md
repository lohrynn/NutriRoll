# Phase 6 — Ratings + History

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 73/73 ✓ vitest 12/12 ✓

---

## What was built

1. **Ratings** — capture user feedback on a bowl (overall 1–5) and optionally per-component 1–5 scores with a free-text comment. Rows are correlated by a client-minted `bowl_id` (UUID) so all per-component ratings for the same plate stay grouped.
2. **History** — append-only event log for `rolled`, `cooked`, `rated` (and reserved `saved`/`discarded`) actions with a JSON `payload` for whatever the source view wants to remember (component names, scores, comments).

## Backend

| Path | Purpose |
|---|---|
| `server/nutriroll/domain/rating.py`, `domain/history.py` | Frozen dataclasses. `Rating.score` validated to `1..5`. `HistoryEvent.payload: dict[str, Any]`. |
| `server/nutriroll/db/models/rating.py`, `models/history.py` | `RatingRow` (FK component SET NULL), `HistoryEventRow` (JSON payload, indexed on `kind`, `bowl_id`, `created_at`). |
| `server/nutriroll/db/repositories/ratings.py`, `repositories/history.py` | Async CRUD. `HistoryRepository.clear()` returns affected rowcount via `getattr(result, "rowcount", 0) or 0` (AsyncSession Result isn't typed). |
| `server/nutriroll/api/schemas/rating.py`, `schemas/history.py` | `extra="forbid"`, `from_domain`. |
| `server/nutriroll/api/routers/ratings.py` | `GET /v1/ratings?bowl_id=…` and `POST /v1/ratings`. FK miss on component → 404 `{code:"component_not_found"}`. |
| `server/nutriroll/api/routers/history.py` | `GET /v1/history?kind=&limit=`, `POST /v1/history`, `DELETE /v1/history/{id}`. |
| `server/alembic/versions/0002_pantry_stores_history.py` | Postgres DDL incl. `CheckConstraint("score BETWEEN 1 AND 5", name="ck_ratings_score_range")`. |
| `server/tests/test_ratings_history_api.py` | 4 tests: bowl rating, per-component rating, history append/list/filter, history delete. |

## Frontend

| Path | Purpose |
|---|---|
| `web/lib/ratings/types.ts`, `web/lib/history/types.ts` | Re-exports + `HISTORY_KINDS` array. |
| `web/components/cook-page.tsx` | "use client". Reads `RolledBowl` from `sessionStorage`, mints a fresh `bowl_id` (`crypto.randomUUID()`) on mount, renders an overall 5-star picker, optional per-component star rows, optional comment. Submit POSTs the overall rating, all per-component ratings (in parallel), and a `kind:"rated"` history event. |
| `web/components/history-page.tsx` | "use client". Loads `/v1/history`, kind-filter chips (All/Rolled/Cooked/Rated), one Card per event with kind badge, optional rating badge, payload preview (component names), formatted timestamp, delete button. |
| `web/app/cook/page.tsx`, `web/app/history/page.tsx` | RSC routes wrapped in `PageShell`. |
| `web/app/me/page.tsx` | `/me` hub: tile grid linking to `/components`, `/pantry`, `/stores`. |

### Wiring history into existing flows

- `web/components/roll-page.tsx` — after a successful `POST /v1/roll`, fire-and-forget `POST /v1/history { kind:"rolled", payload:{components:…} }`. On "Cook now", also fire `kind:"cooked"`.

## Key decisions

- **Client-minted `bowl_id`** keeps the rating row coherent without a server-side bowls table. The same `bowl_id` is later attached to the `rated` history event so the UI can correlate.
- **JSON `payload`** for history events keeps the model open without per-kind tables. Renderers do best-effort lookups (`payload.components`, `payload.overall`).
- **Fire-and-forget telemetry.** History POSTs from roll/cook paths are unawaited and never block UX; the unit-test mock special-cases `/v1/history` so it doesn't consume queued mock responses.
- **`<output aria-live="polite">` everywhere** for status banners — Biome's `useSemanticElements` rule accepts `<output>` and rejects `<div role="status">`.

## Invariants

- `score ∈ [1, 5]` enforced in the domain, the schema, and as a DB `CheckConstraint`.
- History is append-only from the user's perspective; the only mutation is `DELETE /v1/history/{id}` for trimming noise.
- Ratings persist even if the referenced component is later deleted (FK SET NULL).
