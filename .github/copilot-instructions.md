# NutriRoll — Copilot Agent Instructions

This file is injected automatically before every agent prompt. Keep it
accurate and concise. Add facts here when new patterns or conventions are
established; remove them when they are superseded.

---

## Project overview

NutriRoll is a mobile-first installable PWA that rolls randomised bowl-style
meals from a curated ingredient library. It scores and samples components
using a framework-free domain algorithm and provides a full meal-planning,
shopping, cooking, and rating loop.

Single-user, anonymous (device-token auth). No accounts in v1.

---

## Repo structure

```
server/          FastAPI + SQLAlchemy + Alembic backend (Python 3.13, uv)
  nutriroll/
    domain/      Framework-free pure types and business logic — no FastAPI/SQLAlchemy here
    db/          ORM models + async repositories
    api/         Routers + Pydantic v2 schemas
    tools/       CLI utilities (seed loader, OpenAPI dumper)
  alembic/       Migrations (Postgres DDL — do NOT use SQLite-only types here)
  tests/         pytest; SQLite in-memory via dependency_overrides — no Docker needed

web/             Next.js 15 App Router + React 19 + TypeScript strict frontend
  app/           Route segments (each has a page.tsx; heavy logic lives in components/)
  components/    Page-level client components (one per page, named *-page.tsx)
  lib/
    api/         Generated OpenAPI client (schema.d.ts + openapi.json — DO NOT hand-edit)
    components/  Shared component types (types.ts)
  messages/      next-intl translations (en.json + de.json must stay in parity)
  i18n/          next-intl server config

data/seed/       components.csv + cooking_methods.csv — canonical seed data
docs/
  adr/           Architecture Decision Records — immutable once merged; supersede with a new one
  phases/        Per-phase build logs — do not rewrite history; add new phases
  modularity-audit.md  Living document — extend whenever a new modularity gap is found
tools/seed/      Host-side seed runner (calls server package)
```

---

## Commands

| Goal | Command |
|---|---|
| Start dev stack | `make dev` (Docker: postgres + backend + frontend) |
| Stop stack | `make down` |
| Lint + typecheck + test | `make check` ← run this before finishing any task |
| Lint only | `make lint` (ruff + biome) |
| Typecheck only | `make typecheck` (pyright strict + tsc strict) |
| Format | `make fmt` (ruff format + biome format --write) |
| Run tests | `make test` (pytest + vitest) |
| Apply DB migrations | `make migrate` |
| Load seed data | `cd server && NUTRIROLL_DATABASE_URL=postgresql+asyncpg://nutriroll:nutriroll@localhost:5432/nutriroll uv run python -m nutriroll.tools.seed` |
| Regenerate TS client | `make gen-client` (run after any backend schema change) |
| Open DB shell | `make db-shell` |
| Open backend shell | `make server-shell` |

**`make check` must pass before any task is considered done.**

---

## Stack at a glance

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript strict, Tailwind CSS v4 (CSS-first, OKLCH tokens), shadcn/ui, next-intl |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic, Python 3.13, uv |
| Database | PostgreSQL 17 (dev via Docker on port 5432) |
| API contract | OpenAPI → `make gen-client` → `web/lib/api/schema.d.ts` |
| Tests (server) | pytest + httpx; SQLite in-memory; no Docker required |
| Tests (web) | Vitest + RTL; Playwright for e2e |
| Linting | ruff (server) + biome (web) |
| Auth | Anonymous `X-Device-Id` device token; no accounts in v1 |

---

## Architecture rules

### Domain layer is framework-free
`server/nutriroll/domain/` contains only pure Python dataclasses and
functions. **No FastAPI, SQLAlchemy, Pydantic, or any framework import
is allowed here.** All translation between domain types and framework
types lives in `db/repositories/` and `api/schemas/`.

### TypeScript client is generated — never hand-edit
`web/lib/api/schema.d.ts` and `web/lib/api/openapi.json` are produced by
`make gen-client`. Editing them by hand will be overwritten on the next
regeneration.

### Migrations are Postgres-only DDL
`alembic/versions/` files use `postgresql.UUID` and `postgresql.JSONB`.
Tests bypass Alembic entirely via `Base.metadata.create_all` on SQLite.
Do not add SQLite-only constructs to migrations.

### i18n parity
Every key in `web/messages/en.json` must have a corresponding key in
`web/messages/de.json` and vice versa. Rich text uses XML-style tags
(`<link>…</link>`) rendered via `t.rich()`.

### Date formatting — use `useLocale()`
All `toLocaleDateString()` / `toLocaleString()` calls in client components
must receive the locale from `useLocale()` (next-intl) to avoid
server/client hydration mismatches.

### Component vocabulary is fetched, not hardcoded
Categories, allowed cooking methods per category, portion units, and
per-category `balanced_targets` (used by `_nutrition_fit()`) are served by
`GET /v1/meta/components` and consumed in the frontend via the
`ComponentMetaProvider` (in `web/app/layout.tsx`) and the
`useComponentMeta()` / `useCategories()` / `useAllowedMethods()` hooks
from `web/lib/components/meta.tsx`. Do **not** re-introduce hand-maintained
`CATEGORIES` or `ALLOWED_METHODS` constants. Per-category nutrition targets
live in `server/nutriroll/domain/category_meta.py` (`BALANCED_TARGETS`,
overridable via `NUTRIROLL_BALANCED_TARGETS_JSON`) and must not be
duplicated inside `roll.py`.

### FeatureWeights accepts forward-compat extras
`FeatureWeights` (in `server/nutriroll/domain/roll.py`) has seven well-known
weights plus an `extra_weights: Mapping[str, float]` bucket. `FeatureWeightsSchema`
uses `extra="allow"` so unknown numeric weights round-trip end-to-end and land
in `extra_weights`. Extras are validated (non-empty key, non-negative, no
collision with well-known names) but currently do not contribute to
`score_component()` — they are reserved for forthcoming signals
(e.g. `seasonal_bonus`, `eco_score`).

### Macros are JSONB-backed and forward-extensible
`components.macros` is a single JSONB column. The domain `Macros` dataclass
exposes five well-known fields (`kcal`, `carbs_g`, `protein_g`, `fat_g`,
`fiber_g`) plus an `extra: tuple[(str, float), ...]` bucket. `MacrosSchema`
uses `extra="allow"` and round-trips unknown numeric fields. The frontend
form iterates `MACRO_KEYS` from `web/lib/components/types.ts` — adding a new
well-known macro means appending to that list and adding a translation key
under `components.form.<key>`. Forward-compat macros (e.g. `sodium_mg`)
flow end-to-end without any schema change.

### sessionStorage key ownership
`nutriroll.rolledBowl` in sessionStorage is written **only** by the Roll
page (`ROLLED_BOWL_STORAGE_KEY` from `@/lib/recipe/storage`). No other
component should write this key.

---

## Invariants — must never be regressed

These invariants are derived from `docs/phases/`. Violating any of them
is a bug regardless of whether tests catch it.

**Security**
- `middleware.ts` CSP: no `unsafe-inline` scripts, `strict-dynamic`, nonce injected per request.
- Blacklisted components must never appear in a rolled bowl (hard filter in `domain/roll.py`).
- Components whose allergens match `RollRequest.allergens_excluded` must never appear in a rolled bowl.

**Roll algorithm**
- `roll(…)` is deterministic when `RollRequest.seed` is set.
- The algorithm has zero dependencies on FastAPI, SQLAlchemy, or any LLM client.
- A component with no overlapping direction tags scores `direction_match = 0` (neutral) — direction never excludes components.
- `roll(request).slots` always has the same shape regardless of direction selection.

**API**
- `EmptyCandidatePoolError` → 422. All other domain exceptions → 500.
- `Recipe.total_minutes == max(block.total_minutes)` (parallel cook model).
- `score ∈ [1, 5]` enforced at domain + schema + DB (`CheckConstraint`).
- `portions ∈ [1, 20]` for shopping requests.
- Shopping `total_price` = sum of `line_price`s, rounded to 2 dp.

**Data model**
- Saved/planned meal rows store a full JSON snapshot of the bowl — they survive component CRUD.
- History is append-only; the only mutation is `DELETE /v1/history/{id}`.
- Deleting a store cascades to its prices but leaves pantry and components intact.
- PATCH endpoints treat omitted fields as "no change" (None = untouched).

**Tooling**
- `pyright` strict + `ruff` strict must stay at 0 errors.
- Biome `useSemanticElements` rule is active — use `<output>` not `<div role="status">`.
- `lib/api/schema.d.ts` and `lib/api/openapi.json` are excluded from Biome (auto-generated).

---

## Known open issues

See **`docs/modularity-audit.md`** for the full living modularity audit.
All previously open issues (M4, M6, M9, M10) have been resolved. The only
remaining non-issue notes are the intentional forward-compat gaps: `extra_weights`
in `FeatureWeights` are round-tripped but not yet scored, pending future
signals like `seasonal_bonus` or `eco_score`.

See **`docs/phases/`** for per-phase feature backlogs and out-of-scope items.

Key unimplemented features (frontend TODOs):
- Pantry items can only be removed, not edited.
- Plan page has no per-day meal slot picker (Roll page now has one for "Plan today").
- Recipe page has no live countdown timers (steps are static).
- Settings recommendation weights are read-only display; no DB persistence.

---

## Workflow conventions

- **Before any task**: read the relevant phase doc in `docs/phases/` to understand what was already built and why.
- **After any backend schema change**: run `make gen-client` to keep the TS client in sync.
- **After any change**: run `make check`. Do not hand off until it passes.
- **Versioning discipline**: this is a Git repository. After completing a
  cohesive change (a single phase, a single modularity-audit fix, a feature),
  commit it with `git add -A && git commit -m "<message>"`. Write a concise
  imperative-mood subject line and a bullet list body describing what changed.
  Do **not** let uncommitted work pile up across many unrelated features — it
  makes review and rollback impossible. Never run `git push`,
  `git reset --hard`, or any history-rewriting command without explicit user
  confirmation. The user owns push cadence; the agent owns local commits.
- **New phase or feature**: add a phase doc to `docs/phases/` following the existing format.
- **New modularity concern**: add it to `docs/modularity-audit.md` immediately.
- **Resolving a modularity issue**: **remove** the entire section from
  "Open Issues" and add a full entry (description + resolution note) to
  "Resolved Issues" in numeric order. Do **not** leave a `✅ Resolved` stub
  in "Open Issues" — the section must contain only genuinely unresolved items.
  Duplicate stubs (same issue in both sections) are always wrong.
- **Architecture decision**: add an ADR to `docs/adr/` (never edit an existing merged ADR).

### Keeping this file current

**This file must be updated by the agent whenever:**
- A new architecture rule or convention is established (add it to the relevant section).
- An invariant is added or removed (keep the Invariants section in sync with `docs/phases/`).
- A known open issue is resolved (remove it from the list) or a new one is confirmed (add it).
- A new workflow step becomes standard practice (add it above).
- Any fact in this file turns out to be wrong or outdated (fix it immediately).

Treat this file as the single source of agent-facing truth for this repo.
Stale instructions are worse than no instructions — remove anything superseded.
