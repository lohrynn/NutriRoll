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
