# Phase 12 — Meal-prep mode (multi-portion roll)

**Status:** TODO (not started)

---

## Goal

Roll a single bowl that is **cooked once and eaten N times**. The user
selects "Prep N portions" on the Roll page; the algorithm scales the
recipe, the shopping list aggregates ingredients across portions, and the
plan/save snapshot tracks how many portions remain.

This is the natural extension of Phase 11 — once a user can say "50 g
protein per meal", they need a way to actually *prepare* multiple meals
at once.

---

## Backend

- `RollRequest.portions: int = 1` (1–14, validated). Algorithm scales
  per-component grams by `portions` and re-checks `time_budget_min` against
  the *parallel-cook* schedule (Phase 3 model already supports this) but
  with multiplied portion sizes.
- New `Recipe.scaled_portions` field on the recipe schema; existing
  `Recipe.total_minutes` invariant unchanged (parallel cook).
- `POST /v1/shopping-list` accepts `portions` already (Phase 5); ensure
  the saved/planned snapshot also persists `portions` so the shopping
  list can be re-derived later.
- New `planned_meals.portions_remaining: int` column so the planner can
  decrement as the user marks portions eaten (1 prep → 3 daily ticks).

## Frontend

- Roll page: "Portions" stepper (1–14) next to time budget.
- Recipe page: ingredient amounts and step descriptions reflect the
  scaled portions.
- Plan page: a single prep entry surfaces on each day until
  `portions_remaining` hits 0; "Mark eaten" decrements.

## Decisions to make

- Cap on portions (14? 7? a week of lunches feels right).
- Whether the prep is one row in `planned_meals` (with a remaining
  counter) or N rows with a `prep_group_id`. Counter is simpler;
  per-day analytics later may want the group.

## Out of scope

- Cook-time penalty for very large batches (oven capacity, etc.) —
  belongs to the equipment phase.
- Storage / shelf-life suggestions per prep — needs ingredient-level
  shelf-life data not yet in seed.
