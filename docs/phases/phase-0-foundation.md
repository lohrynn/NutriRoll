# Phase 0 — Project Scaffold & API Foundation

**Status:** Done  
**Commit:** `chore: Phase 0 — project scaffold and API foundation`  
**make check:** ruff ✓ biome ✓ pyright ✓ tsc ✓ pytest 1/1 ✓ vitest 2/2 ✓

---

## What was built

Scaffolded the entire mono-repo: Python backend with FastAPI + health-check endpoint, Next.js 15 frontend with CSP middleware, typed API client, i18n wiring, and all tooling/CI plumbing. No application features — purely the load-bearing skeleton.

---

## Files created

### Root
| Path | Purpose |
|---|---|
| `.editorconfig` | Unified indent/charset rules across editors |
| `.gitignore` | Excludes venv, node_modules, .next, .env, caches |
| `.nvmrc` | Node 22 pin for toolchain consistency |
| `.python-version` | Python 3.13 pin for uv |
| `Makefile` | `make check` = ruff + biome + pyright + tsc + pytest + vitest |
| `README.md` | Quick-start and project overview |
| `docker-compose.yml` | Local Postgres 17 + adminer for dev |
| `lefthook.yml` | Pre-commit: ruff fix, biome check, pyright, tsc |
| `docs/adr/README.md` | ADR index |
| `docs/adr/0001-tech-stack.md` | Tech-stack ADR (accepted) |

### Backend (`server/`)
| Path | Purpose |
|---|---|
| `pyproject.toml` | uv project: FastAPI, SQLAlchemy, Alembic, structlog, pytest, etc. |
| `.env.example` | Env var template |
| `nutriroll/__init__.py` | Package root |
| `nutriroll/api/__init__.py` | |
| `nutriroll/api/app.py` | `create_app()` factory; mounts healthz router |
| `nutriroll/api/routers/__init__.py` | |
| `nutriroll/api/routers/healthz.py` | `GET /healthz` → `{version, status}` |
| `nutriroll/db/__init__.py` | |
| `nutriroll/db/session.py` | Async SQLAlchemy engine + `get_session` dependency |
| `nutriroll/db/base.py` | `Base = DeclarativeBase()` |
| `nutriroll/db/models/__init__.py` | Package (empty in Phase 0) |
| `nutriroll/domain/__init__.py` | |
| `nutriroll/tools/__init__.py` | |
| `nutriroll/tools/dump_openapi.py` | `python -m nutriroll.tools.dump_openapi` → stdout JSON |
| `alembic.ini` | Alembic config pointing at `alembic/` |
| `alembic/env.py` | Async migrations env; imports Base.metadata |
| `alembic/versions/.gitkeep` | |
| `tests/__init__.py` | |
| `tests/conftest.py` | SQLite in-memory override for `get_session` |
| `tests/test_healthz.py` | 1 test: `GET /healthz` returns 200 + version |

### Frontend (`web/`)
| Path | Purpose |
|---|---|
| `next.config.ts` | Serwist PWA, env pass-through |
| `tsconfig.json` | Strict, noUncheckedIndexedAccess, exactOptionalPropertyTypes, paths `@/*` |
| `biome.json` | Formatter + linter config; a11y recommended rules |
| `vitest.config.ts` | jsdom, globals, alias `@/*` |
| `middleware.ts` | Per-request CSP nonce, strict-dynamic, no unsafe-inline |
| `app/layout.tsx` | Root layout: NextIntlClientProvider + locale detection |
| `app/page.tsx` | Phase 0 placeholder with `<HealthCheck />` |
| `components/health-check.tsx` | Client component calling `GET /healthz` with `<output aria-live>` |
| `lib/api/client.ts` | `apiClient = createClient<paths>({ baseUrl })` |
| `lib/api/openapi.json` | Generated OpenAPI spec (healthz only) |
| `lib/api/schema.d.ts` | Generated TS types |
| `lib/utils.ts` | `cn()` from clsx + tailwind-merge |
| `messages/en.json` | `{}` (populated Phase 1) |
| `messages/de.json` | `{}` (populated Phase 1) |
| `i18n/request.ts` | next-intl server config with locale detection |
| `tests/setup.ts` | `@testing-library/jest-dom/vitest` import |
| `tests/unit/utils.test.ts` | 2 tests for `cn()` |
| `public/manifest.webmanifest` | PWA manifest |

### Seed data (`data/seed/`)
| Path | Purpose |
|---|---|
| `components.csv` | Starter rows (populated Phase 1 Step 2) |
| `cooking_methods.csv` | Method metadata |
| `dietary_tags.csv` | Canonical tag list |
| `flavor_tags.csv` | Canonical tag list |

---

## Invariants established (future agents must not regress)

- `middleware.ts` CSP must remain: no `unsafe-inline` script, `strict-dynamic`, nonce injected per request.
- Biome a11y `useSemanticElements` rule is active — use `<output>` not `<div role="status">`.
- `lib/pwa/sw.ts` is excluded from both `tsconfig.json` and `biome.json` (uses WebWorker lib).
- `lib/api/schema.d.ts` and `lib/api/openapi.json` are excluded from Biome (auto-generated).
- Test strategy: SQLite in-memory via `app.dependency_overrides[get_session]`. No Docker needed for unit/integration tests.
- `pyright` strict + `ruff` strict must stay at 0 errors. `make check` is the gate.
