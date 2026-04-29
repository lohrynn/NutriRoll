# Implementation Phase Logs

Each file here documents one implementation phase: what was built, every file created or modified, tests that passed, and anything a future agent needs to know before continuing.

## Convention

File naming: `phase-<N>-<slug>.md`  
Phases map directly to the milestone list in `PROJECT_VISION.md § "MVP scoping (what to build first)"`.

## Index

| File | Status | Summary |
|---|---|---|
| [phase-0-foundation.md](phase-0-foundation.md) | ✅ Done | Project scaffold, FastAPI health-check, Next.js shell, CI wiring |
| [phase-1-step-1-component-library.md](phase-1-step-1-component-library.md) | ✅ Done | Component domain + CRUD API + manual editor UI |
| [phase-1-step-2-seed-loader.md](phase-1-step-2-seed-loader.md) | ✅ Done | CSV → DB idempotent seed loader (70 components) |
| [phase-1-step-3-roll-algorithm.md](phase-1-step-3-roll-algorithm.md) | ✅ Done | Pure-function roll algorithm (Steps A–F) + hypothesis tests |
| [phase-2-step-1-roll-api.md](phase-2-step-1-roll-api.md) | ✅ Done | `POST /v1/roll` and `POST /v1/roll/slot` endpoints |
| [phase-2-step-2-roll-page.md](phase-2-step-2-roll-page.md) | ✅ Done | `/roll` page: constraints form, bowl rendering, single-slot reroll |
| [phase-3-step-1-recipe-api.md](phase-3-step-1-recipe-api.md) | ✅ Done | Recipe builder + `POST /v1/recipe` endpoint |
| [phase-3-step-2-recipe-page.md](phase-3-step-2-recipe-page.md) | ✅ Done | `/recipe` page + "Cook now" handoff from Roll |
| [phase-4-pantry.md](phase-4-pantry.md) | ✅ Done | Pantry domain + CRUD API + `/pantry` page |
| [phase-5-stores-shopping.md](phase-5-stores-shopping.md) | ✅ Done | Stores CRUD + per-store prices + `POST /v1/shopping-list` + `/stores` and `/shop` pages |
| [phase-6-ratings-history.md](phase-6-ratings-history.md) | ✅ Done | Ratings (overall + per-component) + append-only history feed + `/cook`, `/history`, `/me` pages |
| [phase-7-directions.md](phase-7-directions.md) | ✅ Done | Direction chips (cuisine/mood) + flavor-axis sliders + per-portion nutrition summary |
| [phase-8-planning.md](phase-8-planning.md) | ✅ Done | Saved meals + week-view planner (`/saved`, `/plan`) + Save/Plan-today actions on Roll |
| [phase-9-onboarding.md](phase-9-onboarding.md) | ✅ Done | `UserProfile` (`/v1/me/profile`) + 3-step `/onboarding` flow + Roll auto-prefill |
| [phase-10-settings.md](phase-10-settings.md) | ✅ Done | `/settings` page (profile editor, appearance, data export, about) |
| [phase-11-nutrition-targets.md](phase-11-nutrition-targets.md) | ✅ Done | Per-meal macro targets (≥/=/≤ per macro) — algorithm + Roll UI + profile defaults |
| [phase-12-meal-prep.md](phase-12-meal-prep.md) | ✅ Done | Multi-portion roll: `portions` on RollRequest + `portions_total/remaining` on planned meals + `mark-eaten` API |
| [phase-13-equipment.md](phase-13-equipment.md) | 🟡 TODO | Equipment profile filters allowed cooking methods |
| [phase-14-cooking-timers.md](phase-14-cooking-timers.md) | 🟡 TODO | Live per-step countdown timers + PWA notifications on Cook page |
| [phase-15-ai-assistant.md](phase-15-ai-assistant.md) | 🟡 TODO | BYO LLM: goal interpretation, recipe customization, week planning |
| [phase-16-notifications.md](phase-16-notifications.md) | 🟡 TODO | PWA push: planner reminders, expiring pantry, weekly summary |
| [phase-17-macro-history.md](phase-17-macro-history.md) | 🟡 TODO | Nutrition tracking dashboard: actual vs target over time |
