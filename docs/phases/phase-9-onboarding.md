# Phase 9 — User profile + 3-step onboarding

## Goal

Give every user a persistent profile (dietary mode, allergens, locale, time
budget, goal) and a 30-second onboarding flow that captures the two filters
that matter most for the Roll algorithm: **dietary mode** and **allergens**.

## Backend

- `domain/profile.py` — `UserProfile` frozen dataclass with validation on
  `dietary_mode` (`""`/`vegan`/`vegetarian`/`pescatarian`),
  `default_time_budget_min` (`> 0` if set), allergens (tuple of strings).
- `db/models/profile.py` — Singleton table `user_profile` with `id = 1`,
  JSONB `allergens`, `updated_at` via `func.now()`.
- `db/repositories/profile.py` — `UserProfileRepository.get_or_create()`
  lazily inserts the singleton row on first GET; `update()` replaces it.
- `api/schemas/profile.py` — `UserProfileRead` / `UserProfileUpdate`
  Pydantic models with strict `extra="forbid"` and a `Literal` dietary mode.
- `api/routers/profile.py` — `GET /v1/me/profile` (creates default if
  missing) and `PUT /v1/me/profile` (full replace).
- `alembic/versions/0004_user_profile.py` — Postgres-only DDL with JSONB.

## Frontend

- `lib/profile/types.ts` — Re-exports `UserProfileRead`/`UserProfileUpdate`,
  plus `DIETARY_MODES` and `COMMON_ALLERGENS` constants.
- `components/onboarding-page.tsx` — 3 controlled steps:
  1. Welcome + value proposition.
  2. Dietary mode chips (Any / Vegan / Vegetarian / Pescatarian).
  3. Allergen multi-select chips (`COMMON_ALLERGENS`).

  Submitting `PUT`s the profile with `onboarded: true` and routes to `/roll`.
- `app/onboarding/page.tsx` — `PageShell` wrapper.
- `components/roll-page.tsx` — On mount, fetches `/v1/me/profile` and
  prefills `dietaryMode`, `allergensCsv`, and `timeBudgetMin` _only_ if the
  user hasn't already typed something. This keeps the page fully usable
  for fresh visitors while honoring saved preferences.
- `messages/{en,de}.json` — Full `onboarding.*` namespace (welcome copy,
  dietary copy, allergen labels for all 9 common tags) with parity.

## Tests (4 new, 88 total)

- `test_profile_default_get_creates_singleton`
- `test_profile_put_round_trip`
- `test_profile_rejects_unknown_dietary_mode` (422)
- `test_profile_rejects_non_positive_time_budget` (422)

`make check` is green: ruff + pyright + biome + tsc + 88 pytest + 12 vitest.

## Notes / future work

- No middleware redirect to `/onboarding` (yet) — the entry path is via the
  `/me` tile. A server-side redirect would require an absolute API URL or
  a cookie set after the PUT; deferred to Phase 10 when settings live.
- `goal` is stored but not yet exposed in the UI; reserved for Phase 10
  ("more protein", "lose weight", etc.) so the algorithm can re-weight.
