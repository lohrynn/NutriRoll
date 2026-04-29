# Phase 13 — Equipment & kitchen profile

**Status:** TODO (not started)

---

## Goal

Some users don't have an oven. Some only own a single pan. Filter
`ALLOWED_METHODS` per category by what the user actually owns, so the
algorithm never proposes a sheet-pan dish to someone with only a hot
plate.

---

## Backend

- New `domain/equipment.py` with an `Equipment` StrEnum
  (`oven`, `stovetop`, `microwave`, `air_fryer`, `pressure_cooker`,
  `blender`, `grill`, …) and a `METHOD_REQUIREMENTS: Mapping[CookingMethod,
  frozenset[Equipment]]` map (single source of truth, like
  `ALLOWED_METHODS`).
- `UserProfile.equipment: frozenset[Equipment]` — empty = "all
  available" (back-compat default; existing rolls unchanged).
- `RollRequest.available_equipment: frozenset[Equipment]` propagated
  from profile.
- `roll()` filters out components whose only allowed methods require
  unavailable equipment (hard filter, like blacklist).
- Migration `0009_profile_equipment.py` — JSON column.
- `GET /v1/meta/components` exposes `method_requirements` and
  `equipment` enum values (next-step in M4 follow-up — see audit).

## Frontend

- Onboarding step (or settings card): equipment chip toggles with
  sensible defaults pre-selected (oven + stovetop + microwave).
- Roll page surfaces a small icon strip showing which equipment the
  current bowl uses.

## Out of scope

- Equipment-specific cook-time adjustments (air fryer is faster than
  oven for the same dish).
- Equipment-aware recipe step rewording.

## Implementation log (built)

Backend:

- New domain module `nutriroll/domain/equipment.py` exporting the `Equipment`
  StrEnum (oven, stovetop, microwave, air_fryer, pressure_cooker, blender,
  grill, toaster), a frozen `METHOD_REQUIREMENTS` map (one entry for every
  member of `CookingMethod`, asserted by `test_equipment.py`), a
  `DEFAULT_EQUIPMENT` set, and helpers `method_is_available` /
  `component_is_equipment_feasible` / `filter_components_by_equipment`.
  Empty available-set is treated as "all available" (back-compat).
- `UserProfile.equipment: tuple[Equipment, ...]` with `__post_init__`
  duplicate check and a `available_equipment()` helper.
- `RollRequest.available_equipment: frozenset[Equipment]` plus a new
  `_passes_equipment` hard filter wired into `filter_candidates`. Forwarded
  through `reroll_slot` and the router's `_with_pantry` reconstruction so
  rerolls keep the same equipment context.
- `UserProfileRead/UserProfileUpdate` and `RollRequestSchema` use
  `list[Equipment]` so the OpenAPI schema (and generated TS client) carry
  the union of literal values rather than `string[]`.
- `GET /v1/meta/components` now exposes `equipment`, `default_equipment`,
  and `method_requirements` so the frontend never duplicates the
  enum-to-equipment mapping.
- ORM column `user_profile.equipment` (JSON in code, JSONB on Postgres).
  Migration `0010_profile_equipment.py`. Repository (de)serialises and
  silently drops unknown enum values to keep older profiles loadable.
- Tests: `tests/test_equipment.py` covers the helper, default set, and the
  "every method has a requirement" anti-regression. `test_meta_api.py` /
  `test_profile_api.py` updated for the new fields.

Frontend:

- New types: `Equipment` exported from `lib/components/types.ts`. New
  hooks `useEquipment`, `useDefaultEquipment`, `useMethodRequirements` in
  `lib/components/meta.tsx`.
- `components/settings-page.tsx`: new "Kitchen equipment" card with chip
  toggles fed by `useEquipment()`. New profiles pre-fill with
  `default_equipment` (oven + stovetop + microwave) once meta arrives,
  unless the user has already touched the chips. Equipment is included
  in every PUT body alongside weights and macro targets.
- `components/roll-page.tsx`: seeds `availableEquipment` from the profile
  on first mount and forwards it as `available_equipment` in every roll
  body so the algorithm filters infeasible bowls server-side.
- i18n: `settings.equipment.*` keys in `messages/en.json` + `messages/de.json`.
- TS client regenerated via `make gen-client` after the OpenAPI bump.

`make check` is green: 108 server tests, 12 web tests, ruff/biome clean,
pyright + tsc strict at zero errors.
