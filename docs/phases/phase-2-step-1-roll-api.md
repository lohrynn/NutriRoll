# Phase 2 Step 1 — Roll API Endpoints

**Status:** Done
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 40/40 ✓ vitest 6/6 ✓

---

## What was built

HTTP surface around the pure-function roll algorithm from Phase 1 Step 3. Two endpoints:

- `POST /v1/roll` — roll a full bowl. Loads the live (non-blacklisted) component pool from the DB, runs `nutriroll.domain.roll.roll(...)`, returns one `RolledSlot` per requested slot with score + top-2 reasons.
- `POST /v1/roll/slot` — re-roll a single slot, excluding the previously-chosen component for that slot. Server stays stateless; the client splices the returned slot into its local bowl.

## Files created

| Path | Purpose |
|---|---|
| `server/nutriroll/api/schemas/roll.py` | Pydantic v2 schemas: `SlotSpecSchema`, `FeatureWeightsSchema`, `RollRequestSchema` (with `to_domain()`), `RolledSlotSchema`/`RolledBowlSchema` (with `from_domain()`), `RerollSlotRequestSchema`. |
| `server/nutriroll/api/routers/roll.py` | `POST /v1/roll` and `POST /v1/roll/slot`. Maps `EmptyCandidatePoolError` → `422 {code: "empty_candidate_pool", category, reason}`. |
| `server/tests/test_roll_api.py` | 6 tests: returns one-per-slot, deterministic with seed, allergen exclusion empties pool → 422, blacklist empties pool → 422, reroll endpoint, request validation. |

## Files modified

| Path | Change |
|---|---|
| `server/nutriroll/api/app.py` | Mount `roll.router`. |
| `web/lib/api/openapi.json` + `web/lib/api/schema.d.ts` | Regenerated to include roll endpoints/schemas. |

## Key technical decisions

| Decision | Reason |
|---|---|
| `HTTP_422_UNPROCESSABLE_CONTENT` | Starlette deprecated `HTTP_422_UNPROCESSABLE_ENTITY`. Tests run with `filterwarnings=error`, so the legacy alias would fail pytest. |
| Reroll endpoint takes the full request (not a server-side bowl id) | Server stays stateless. The client already has the bowl in memory; re-roll is just "give me one more slot of this category, excluding these ids". |
| Whole pool loaded per request (no DB-side filter) | Pool is small (~80 rows in v1). All filtering is the algorithm's job and cleanly separated from persistence. Revisit when the pool grows. |
| `default_factory=list[UUID]` (not bare `list`) | pyright strict mode requires a parameterised factory to infer element type; bare `list` produces `list[Unknown]`. |

## Invariants added

- `EmptyCandidatePoolError` is the only domain exception that the roll endpoints translate to a 422; everything else propagates as a 500 (programmer error).
- `web/lib/api/schema.d.ts` and `web/lib/api/openapi.json` must be regenerated whenever a roll schema changes.
