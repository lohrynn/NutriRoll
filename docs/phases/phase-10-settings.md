# Phase 10 — Settings page

## Goal

A single `/settings` route that exposes everything from onboarding (and a
few extras) for editing, plus appearance, recommendations transparency,
data export and an "About" footer.

This phase intentionally **does not add new backend endpoints** — Phase 9
already shipped `/v1/me/profile`, and Phase 5/6/8 shipped components,
saved meals, planned meals and history endpoints which the JSON export
just calls.

## Frontend

- `app/settings/page.tsx` — `PageShell` wrapper.
- `components/settings-page.tsx` — Single client component with five
  cards:
  1. **Profile** — `Select` for dietary mode, allergen chip toggles,
     numeric `Input` for default time budget (validated > 0), text input
     for goal. `PUT /v1/me/profile` on save with `onboarded: true` so
     editing settings counts as onboarded.
  2. **Appearance** — three buttons (System / Light / Dark) that write
     `nutriroll.theme` to `localStorage` and set `data-theme` on `<html>`.
  3. **Recommendations** — read-only `Badge` chips listing the default
     `FeatureWeights` (price / nutrition / novelty / direction match /
     rating). Tuning is documented as future work.
  4. **Data** — "Export JSON" downloads a bundle of profile, components,
     saved, planned, history. "Reset local theme" clears the override.
  5. **About** — version + tagline.
- `app/me/page.tsx` — Adds Settings tile (after the existing tiles).
- `app/layout.tsx` — Adds a small pre-paint `<script>` (with the CSP
  nonce from `x-nonce` header) that reads `localStorage("nutriroll.theme")`
  and sets `data-theme` on `<html>` before first paint to avoid flashes.
- `app/globals.css` — Adds explicit `:root[data-theme="light"]` and
  `:root[data-theme="dark"]` blocks so the user override beats the
  `prefers-color-scheme` media query, and sets `color-scheme`.
- `messages/{en,de}.json` — Full `settings.*` namespace + `home.tiles.settings`
  with parity.

## Tests

No new tests — all changes are wired-up UI calling existing endpoints and
re-using the Phase 9 profile contract. `make check` is green: 88 pytest
+ 12 vitest, ruff + pyright + biome + tsc clean.

## Out of scope (future)

- Editable algorithm weights (would need a `roll_weights` table).
- Blacklist manager (would need a `disliked_components` table and a
  `disliked_ids` set in `RollRequest`).
- Notifications / equipment / kitchen toggles / units / currency.
- Account deletion (single-user singleton; no auth yet).
- LLM features (BYO-key) — explicitly deferred until the AI plumbing
  lands.
