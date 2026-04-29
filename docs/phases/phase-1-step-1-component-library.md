# Phase 1 Step 1 — Component Library & Manual Editor

**Status:** Done  
**Commit:** `feat: Phase 1 Step 1 — component domain, CRUD API and manual editor UI`  
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 17/17 ✓ vitest 6/6 ✓

---

## What was built

The curated component library (backend + frontend). A `Component` is the atomic unit every rolled bowl is assembled from. This phase adds the full lifecycle: pure domain model, ORM, async repository, Pydantic schemas, FastAPI CRUD router, Alembic migration, typed TS client, and a Next.js manual-entry editor with list view and i18n.

LLM-assisted component creation (§7 option 2) is **explicitly deferred** per MVP scoping.

---

## Files created

### Backend
| Path | Purpose |
|---|---|
| `server/nutriroll/domain/component.py` | Pure-Python domain (no framework). `Category`, `CookingMethod`, `PortionUnit` StrEnums; `ALLOWED_METHODS: dict[Category, frozenset[CookingMethod]]`; frozen slotted dataclasses `Macros`, `Portion`, `CookingMethodSpec`, `Component`. `__post_init__` validates: name non-empty, default method allowed for category, default method appears in cooking_methods list, no duplicate methods, macros ≥ 0, portion value > 0. |
| `server/nutriroll/db/models/component.py` | `ComponentRow(Base)`, `__tablename__="components"`. Uses `sa.Uuid(as_uuid=True)` (dialect-aware, works on both PG and SQLite). JSON columns for cooking_methods, tags, allergens. |
| `server/nutriroll/db/models/__init__.py` | Exports `ComponentRow`; importing this package registers ORM tables on `Base.metadata`. |
| `server/nutriroll/db/repositories/__init__.py` | Package shell. |
| `server/nutriroll/db/repositories/components.py` | `ComponentRepository`: async list/get/create/update/delete. `ComponentNameTakenError` raised on `IntegrityError`. `_row_to_domain` and `_domain_to_columns` helpers. |
| `server/nutriroll/api/schemas/__init__.py` | Package shell. |
| `server/nutriroll/api/schemas/component.py` | Pydantic v2 schemas with `extra="forbid"`. `ComponentBase` has `model_validator` enforcing method-allowed-for-category, no duplicate methods, default in list. Tag lists validated for uniqueness. Each schema has `to_domain()` / `from_domain()` converters. |
| `server/nutriroll/api/routers/components.py` | `APIRouter(prefix="/v1/components")`. Endpoints: `GET ""` (list, query params: category, include_blacklisted, limit, offset), `POST ""` (201), `GET /{id}` (404), `PUT /{id}` (full replace, 404/409), `DELETE /{id}` (204). |
| `server/alembic/versions/0001_components.py` | Manual migration. Creates `components` table with PG-native types (`postgresql.UUID`, `postgresql.JSONB`), unique constraint `uq_components_name`, index `ix_components_category`. `downgrade()` drops index then table. |
| `server/tests/test_component_domain.py` | 7 tests: valid component, empty name rejected, default method must be in methods, method must be allowed for category, duplicate methods rejected, negative macros rejected, zero portion rejected. |
| `server/tests/test_components_api.py` | 9 tests: list empty, create then get, duplicate name → 409, default method not listed → 422, method not allowed for category → 422, filter by category, update replaces fields, delete → 204 then 404, unknown id → 404. |

### Backend — modified files
| Path | Change |
|---|---|
| `server/nutriroll/api/app.py` | Added `components` router: `app.include_router(components.router)` |
| `server/alembic/env.py` | Added `from nutriroll.db import models as _models` (side-effect: registers tables on `Base.metadata`) |
| `server/tests/conftest.py` | Added SQLite+aiosqlite in-memory engine; `Base.metadata.create_all` in fixture; `app.dependency_overrides[get_session]` override |
| `server/pyproject.toml` | Added `aiosqlite>=0.20` to dev deps; added `[tool.ruff.lint.flake8-bugbear] extend-immutable-calls` to suppress B008 false positives on FastAPI DI |

### Frontend
| Path | Purpose |
|---|---|
| `web/lib/components/types.ts` | Re-exports `Category`, `CookingMethod`, `PortionUnit`, `ComponentRead`, `ComponentCreate`, `CookingMethodSpec` from the generated schema. Mirrors `ALLOWED_METHODS` from the Python domain so the form can filter method options client-side without an extra API round-trip. `parseCsvList` helper. |
| `web/components/component-form.tsx` | Client component. Full manual-entry form covering every property from vision §7: category select (filters available cooking methods), name, image URL, default portion (value + unit), macros per 100g (5 fields), cooking methods array (add/remove rows, method select filtered by category, approx_minutes, can_cook_with_others checkbox, notes), default cooking method select (options = current method rows), flavor/dietary/allergen tag inputs (comma-separated), shelf life days, blacklisted toggle. Submits via `apiClient.POST("/v1/components")`. Handles 409 and generic errors with `<output aria-live>`. All strings via `useTranslations`. |
| `web/components/component-manager.tsx` | Client component. Combines list view + inline form. Category filter dropdown. Loading/error/empty states. Optimistic prepend of newly created components to the list without a refetch. |
| `web/app/components/page.tsx` | RSC route at `/components`. Wraps `<ComponentManager />`. |
| `web/tests/unit/component-manager.test.tsx` | 4 tests: renders empty state, renders fetched items, shows error on API failure, submits new component via form. Mocks `apiClient` with `vi.mock`. Wrapped in `NextIntlClientProvider`. |

### Frontend — modified files
| Path | Change |
|---|---|
| `web/messages/en.json` | Populated all i18n keys for components UI: title, subtitle, empty/loading/error, filter chips, row display, all form labels/placeholders/errors, category/method/unit translations |
| `web/messages/de.json` | German translations for all of the above |
| `web/lib/api/schema.d.ts` | Regenerated — now includes `/v1/components` paths and all component schemas |
| `web/lib/api/openapi.json` | Regenerated OpenAPI spec including component endpoints |
| `web/vitest.config.ts` | Added `esbuild: { jsx: "automatic" }` so JSX transforms work without explicit `import React` in test files |

### Docs
| Path | Purpose |
|---|---|
| `docs/phases/README.md` | Phase log index |
| `docs/phases/phase-0-foundation.md` | This file's predecessor |
| `docs/phases/phase-1-step-1-component-library.md` | This file |

---

## Key technical decisions made in this phase

| Decision | Reason |
|---|---|
| `sa.Uuid(as_uuid=True)` instead of `postgresql.UUID(...).with_variant(String(36), "sqlite")` | The variant approach caused SQLite INSERT failures — aiosqlite couldn't bind a Python `UUID` object via that type. `sa.Uuid` is the SQLAlchemy 2.0 dialect-aware type that works on both. |
| `assert _models is not None` after side-effect imports | pyright `reportUnusedImport` fires on `import ... as _models` when the import is only for its side-effect (table registration). The assert keeps pyright satisfied without disabling the rule. |
| Cooking methods mirrored in `web/lib/components/types.ts` | The form must filter the method select by category client-side. Re-fetching allowed methods from the server per-keystroke would be slow and unnecessary; the whitelist is stable and small. |
| `esbuild: { jsx: "automatic" }` in vitest.config.ts | React 19 uses the automatic JSX transform. Without this, vitest's esbuild transform doesn't inject `React` and all JSX in test files throws `React is not defined`. |

---

## Invariants added (must not be regressed)

- The `ALLOWED_METHODS` whitelist in `web/lib/components/types.ts` must stay in sync with `server/nutriroll/domain/component.py::ALLOWED_METHODS`. If the server list changes, update the frontend mirror.
- The `ComponentRow` ORM model uses `sa.Uuid(as_uuid=True)` — do not switch to `postgresql.UUID` without adding the `with_variant` fix for SQLite **and** verifying test aiosqlite binding still works.
- `server/alembic/versions/0001_components.py` is Postgres-only DDL (`postgresql.UUID`, `postgresql.JSONB`). Tests bypass Alembic entirely (SQLite `create_all` from `Base.metadata`).

---

## What's next

Continue Phase 1:
- **Step 2** — Seed loader: `tools/seed/load.py` reads `data/seed/components.csv` + `cooking_methods.csv`, validates via Pydantic, idempotent upsert (skip existing by name). Refuses to run on non-empty prod DB without `--force`. See `data/seed/README.md`.
- **Step 3** — Roll algorithm: pure functions in `server/nutriroll/domain/roll.py` implementing Steps A–F from vision §"Logic 2. Roll Algorithm". Hypothesis property tests for invariants (Steps A + D hard rules). No LLM integration in Step 3 (deterministic only).
