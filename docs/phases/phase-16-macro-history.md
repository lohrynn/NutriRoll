# Phase 16 — Macro tracking dashboard

**Status:** TODO (not started)

---

## Goal

Show the user how their actual eaten macros compare to their targets
(from Phase 11) over time. Daily / weekly / monthly views, per-macro
charts, and a "you hit your protein target 5/7 days last week"
streak summary.

---

## Backend

- New `GET /v1/me/nutrition-summary?from=…&to=…&granularity=day|week`
  endpoint.
- Aggregates from existing `history` rows: each history entry already
  stores a bowl snapshot with macro contributions.
- Compares against `user_profile.default_macro_targets` (Phase 11).

## Frontend

- New `/me/nutrition` route with a date-range picker, five line charts
  (one per well-known macro) and target reference lines.
- `app/me/page.tsx` adds a "Nutrition" tile.
- Use a small headless chart lib (`recharts` or hand-rolled SVG to
  avoid dep bloat — vision §X likely prefers the latter).

## Out of scope

- Goal recommendation ("you're under-eating protein, raise your
  default") — belongs to the AI phase.
- Per-component breakdown ("oats are your top fiber source").
