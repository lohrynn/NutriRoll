# Phase 11 — Per-meal nutrition targets

**Status:** TODO (not started)

---

## Goal

Let the user say "I want a meal that hits **50 g of protein**" — or
"3 prep-meals at **600 kcal each, 30 g fat max**" — and have the roll
algorithm steer toward bowls that meet those targets per portion.

Today the algorithm only knows the *generic* per-category `BALANCED_TARGETS`
in `server/nutriroll/domain/category_meta.py`. There is no way for a user
to say *what they personally want a meal to hit*. This phase makes
nutrition a first-class user-controllable input alongside time-budget and
direction.

This is a fundamental gap: every fitness-driven user (cut, bulk, recomp,
high-protein vegetarian, low-carb) needs this. Without it the app is a
"random bowl roller" rather than a planning tool.

---

## Backend

### Domain (`server/nutriroll/domain/`)

| Path | Change |
|---|---|
| `roll.py` — new `MacroTargets` dataclass | Frozen, framework-free. Fields mirror `Macros`: `kcal: float \| None`, `protein_g: float \| None`, `carbs_g: float \| None`, `fat_g: float \| None`, `fiber_g: float \| None`, plus `extra: tuple[(str, float \| None), ...]`. Each field is **optional** — `None` means "no preference" for that macro; only set fields are scored. Adds a `mode: Literal["target", "min", "max"]` per macro (default `"target"`) so the user can express "≥ 50 g protein" vs "= 50 g protein" vs "≤ 30 g fat". |
| `roll.py` — `RollRequest.macro_targets: MacroTargets \| None = None` | New optional field. `None` keeps existing behavior (only `BALANCED_TARGETS` apply). |
| `roll.py` — `score_component()` | New `macro_target_fit` feature in addition to (not replacing) `nutrition_fit`. Computes per-portion contribution of the candidate component toward each set target, normalized by the target value, summed across slots via the partial-bowl context already passed to `score_component`. For `mode="target"`: triangular distance penalty centered on `target / n_slots`. For `mode="min"`: zero penalty above target, linear ramp below. For `mode="max"`: zero penalty below target, linear ramp above. |
| `roll.py` — `FeatureWeights.macro_target_fit: float = 0.5` | New well-known weight. Defaults high because targets are user-stated intent and should dominate. The existing `nutrition_fit` weight stays in place as a soft fallback; when `macro_targets` is `None`, `macro_target_fit` resolves to `0.0` (neutral) and the algorithm behaves as before. |

### API (`server/nutriroll/api/schemas/roll.py`)

| Path | Change |
|---|---|
| `MacroTargetSchema` (new) | Pydantic v2 model with `value: float \| None`, `mode: Literal["target", "min", "max"] = "target"`. `extra="forbid"`. Validates `value >= 0` when set. |
| `MacroTargetsSchema` (new) | One `MacroTargetSchema` per well-known macro, all `None` by default; `extra="allow"` to round-trip forward-compat macros (mirroring `MacrosSchema`). |
| `RollRequestSchema.macro_targets` | Optional field; `to_domain()` converts to `MacroTargets`. |

### Migration

None required. `MacroTargets` lives only on the request DTO and on the
roll-result snapshot already stored as JSON for saved/planned meals.

### Tests (`server/tests/`)

- `test_roll_algorithm.py`: extend with three deterministic-seed tests:
  one for `mode="target"` (algorithm picks higher-protein components when
  protein target is set), one for `mode="min"` (no penalty above the
  threshold), one for `mode="max"` (algorithm avoids high-fat
  components). Verify `RollRequest(macro_targets=None)` produces the same
  bowl as today (regression guard).
- `test_roll_api.py`: round-trip a request with `macro_targets` set and
  assert the response includes per-portion macro totals (already present
  via `nutrition` summary) and that targets land in the saved snapshot.

---

## Frontend

### `web/components/roll-page.tsx`

- New "Nutrition targets" Card between "Direction" and "Constraints" with:
  - One row per macro in `MACRO_KEYS` (`kcal`, `protein_g`, `carbs_g`,
    `fat_g`, `fiber_g`).
  - Each row: numeric `Input` for value, three-button toggle for mode
    (`≥` / `=` / `≤`), and a "Clear" X button per row.
  - "Clear all" button at the bottom. Empty state: nothing sent.
- `buildRequestBody()` adds `macro_targets` only when at least one row is
  set; otherwise omitted (matches backend `None`).
- Reuse the existing per-portion `nutrition` strip on the rolled bowl
  card to show *actual* totals; add a small badge per macro that turns
  green when target is met (or red/orange when missed) so the user can
  see at a glance whether the roll satisfied the request.

### `web/components/settings-page.tsx`

- New "Default nutrition targets" card under "Recommendations" so the
  user can persist their typical targets (e.g. always 50 g protein).
  Backed by a new `default_macro_targets: dict[str, MacroTargetSchema]`
  field on `UserProfileRead/Update` (sibling of the existing
  `roll_weights` from M6/M10).
- Roll page seeds the form from `profile.default_macro_targets` on mount
  (mirrors existing weights/profile pattern).

### Persistence

- New JSON column `default_macro_targets` on `user_profile` (Alembic
  migration `0008_profile_default_macro_targets.py`, JSON in ORM for
  SQLite-test compat, JSONB in migration). Same pattern as
  `roll_weights` (M6/M10).

### i18n

- New `roll.nutritionTargets.*` namespace and
  `settings.defaultNutritionTargets.*` namespace in `en.json` + `de.json`,
  with parity. Reuse existing `components.macros.*` macro labels.

### TypeScript client

- Run `make gen-client` after backend schema changes.

---

## Key decisions

- **Per-portion, not per-bowl.** Targets are interpreted *per portion*
  (one rolled bowl = one portion at `default_portion`). For meal-prep
  ("3 meals × 50 g protein"), the user sets `protein_g = 50, mode = ">="`
  on a single roll and then taps "Plan today" / "Save" three times. A
  proper meal-prep multi-portion mode is its own phase (see Phase 12
  TODO below).
- **Soft constraint, never a filter.** Like direction, targets *score*
  components and never exclude any. A roll with extreme targets that no
  component combination can hit still returns a bowl — the worst-case is
  a bowl whose `macro_target_fit` is low, which surfaces in the score
  reasons string. This avoids `EmptyCandidatePoolError` for unrealistic
  targets.
- **Three modes per macro.** "target" (closest to value), "min"
  (anything ≥ value is fine), "max" (anything ≤ value is fine). Covers
  the three actual user intents — "I want X", "at least X", "no more
  than X" — without inventing a fourth.
- **`macro_target_fit` is additive, not a replacement for
  `nutrition_fit`.** The latter still covers "balanced macro
  distribution" when the user sets no targets; the former covers
  "absolute target hit" when the user does.
- **Forward-compat via the `extra` bucket.** When the seed CSV adds a
  new macro (e.g. `sodium_mg`) the request schema's `extra="allow"`
  picks it up automatically; only the UI form needs a new row to expose
  it.

---

## Out of scope (deferred)

- Multi-portion meal-prep optimization (cook 3 portions at once, total
  cook time, total grocery list) — Phase 12.
- AI-assisted target inference from goal text ("I want to lose weight"
  → kcal target) — Phase 13 / LLM phase.
- Macro tracking dashboard ("how close was I last week?") — Phase 16.
- Per-day total targets across the planner (vs per-meal) — Phase 17.

---

## Acceptance checklist

- [ ] User can set a per-macro target with mode on the Roll page.
- [ ] Roll request omits `macro_targets` when no row is set; existing
      tests pass unchanged.
- [ ] When set, the rolled bowl meets the target more often than a
      baseline roll without targets (verifiable in
      `test_roll_algorithm.py` with a deterministic seed).
- [ ] Bowl card shows actual macro totals with a per-macro met/missed
      badge.
- [ ] Settings page has editable "Default nutrition targets" backed by
      `user_profile.default_macro_targets`.
- [ ] `make check` passes.
