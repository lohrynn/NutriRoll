# Modularity Audit

> **Living document.** Every agent and developer working on NutriRoll must keep
> this file active and up-to-date. When a new modularity concern is discovered —
> however small — add it here immediately. Resolved items are marked ✅ and kept
> for historical reference; they are never deleted.

---

## What counts as a modularity issue?

A modularity issue exists when adding, removing, or changing one *logical*
thing (a macro nutrient, a category, a scoring signal, a cooking method…)
requires editing **more than one file or layer** to stay consistent. The goal
is that each concept lives in exactly one authoritative place, and all other
layers derive from it.

---

## Open Issues

*No open issues.* All known modularity concerns have been resolved. When a new
one is discovered, add it here following the format in the section below.

---

## Resolved Issues

### M1 — Macros stored as flat DB columns ✅

Replaced the five flat `*_per_100g` Float columns on `components` with a
single `macros` JSONB column (migration `0006_components_macros_jsonb.py`,
backfill in-place). The domain `Macros` dataclass keeps the five well-known
fields first-class plus an `extra: tuple[(str, float), ...]` bucket for
forward-compat keys, with a `from_mapping()` constructor and `as_dict()` view.
`MacrosSchema` is now `extra="allow"` and round-trips unknown numeric fields.
The frontend form iterates `MACRO_KEYS` (typed via `MacroKey`) instead of
five hardcoded `useState` calls.

### M2 — `fiber_g` stored but never used in roll scoring ✅

Added `fiber_g` to `_BALANCED_TARGETS` and `_nutrition_fit()` in
`server/nutriroll/domain/roll.py`. Fiber-rich components now contribute to the
nutrition-fit score.

### M3 — `typical_availability` in seed CSV silently discarded ✅

Added `seasonal_availability: str | None` to the domain `Component`,
the `ComponentRow` ORM, the `MacrosSchema`/`ComponentBase` API schemas, and
the seed loader (which now reads the `typical_availability` CSV column).
Migration: `0005_component_seasonal_availability.py`.

### M4 — `Category` StrEnum: adding a new bowl slot still touches enum + i18n ✅

`GET /v1/meta/components` now returns `category_labels: dict[Category, str]` —
human-readable English display names derived from the Python enum value
(title-cased, underscores to spaces). The frontend `useCategoryLabel(category)`
hook in `web/lib/components/meta.tsx` uses this as a fallback so any new
category is rendered meaningfully without a code change to either translation
file. The i18n pair is still the authoritative source for translated labels;
the API-provided labels serve as an auto-generated safety net.

### M5 — `ALLOWED_METHODS` duplicated in Python and TypeScript ✅

Added `GET /v1/meta/components` returning categories, portion units, and
allowed methods per category. Frontend now consumes the endpoint via
`ComponentMetaProvider` + `useComponentMeta()` / `useCategories()` /
`useAllowedMethods()` hooks. The hand-maintained `CATEGORIES` and
`ALLOWED_METHODS` constants in `web/lib/components/types.ts` are gone.

### M6 — `FeatureWeights` partially extensible; weights not DB-persisted ✅

`roll_weights` JSONB column added to `user_profile` (migration
`0007_profile_roll_weights.py`). `PUT /v1/me/profile` now accepts
`roll_weights: dict[str, float]` and persists them. The settings page seeds
initial slider state from the profile response and fires a PUT on every slider
change; `localStorage` is kept in parallel as a fast offline cache consumed by
`loadWeightsForRoll()` in `roll-page.tsx`. `extra_weights` keys are
round-tripped but intentionally not yet scored — new signals must still extend
`score_component()`.

### M7 — `MacrosSchema` uses `extra="forbid"` blocking API extension ✅

Folded into M1.

### M8 — Nutrition balance targets hardcoded in roll algorithm ✅

Moved the per-category macro targets out of `roll.py` into
`server/nutriroll/domain/category_meta.py` as `BALANCED_TARGETS`
(`MappingProxyType`, framework-free). The same constant is now exposed by
`GET /v1/meta/components` under `balanced_targets`, and can be tuned without
code changes via the `NUTRIROLL_BALANCED_TARGETS_JSON` environment variable
(partial overrides are merged on top of the defaults). Per-user-goal
derivation is still deferred to the NLP/LLM work in
`docs/phases/phase-9-onboarding.md`.

### M9 — `EXPIRY_WARNING_DAYS` duplicated across server and client ✅

Constant moved to `server/nutriroll/domain/category_meta.py` as
`EXPIRY_WARNING_DAYS` (env-overridable via `NUTRIROLL_EXPIRY_WARNING_DAYS`).
Exposed by `GET /v1/meta/components` as `expiry_warning_days: int`. Frontend
reads it via `useExpiryWarningDays()` from `web/lib/components/meta.tsx`;
`web/lib/pantry/freshness.ts` retains `DEFAULT_EXPIRY_WARNING_DAYS = 3` only
as a loading fallback. All `isExpiringSoon()` call sites in `pantry-page.tsx`
now pass the server-provided value.

### M10 — Algorithm weights device-local (`localStorage`) only ✅

Folded into M6. `roll_weights` JSONB column on `user_profile` (migration
`0007`) means weight customisations survive browser clears and device switches.
`localStorage` is kept as a fast offline cache.

---

## How to use this file

1. **Before adding a new domain concept** (field, category, weight, tag…),
   check this file to see if the pattern is already flagged. If so, fix the
   root cause rather than adding to the sprawl.
2. **When you discover a new instance** of a known pattern, add it to the
   relevant issue's table above.
3. **When you find an entirely new pattern**, add a new `### Mx` section
   following the same format: issue name, table of affected locations, impact
   description, recommended fix.
4. **When an issue is fully resolved**, move it to the *Resolved Issues*
   section with a brief note on what was done and which commit/phase it landed
   in.
