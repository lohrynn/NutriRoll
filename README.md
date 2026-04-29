# NutriRoll

A mobile-first installable PWA that recommends bowl-style meals — cheap,
tasty, and explainable. See [`PROJECT_VISION.md`](./PROJECT_VISION.md) for
the source-of-truth vision and tech stack, and
[`docs/adr/`](./docs/adr/) for decision records.

## Quick start

Prereqs: Docker, Make, `pnpm@9`, `uv`, Node 22, Python 3.13.

```bash
make dev              # postgres + backend (uvicorn --reload) + next dev
curl localhost:8000/healthz
open  http://localhost:3000
```

Common targets:

```bash
make check            # lint + typecheck + tests, both projects
make test             # unit tests only
make migrate          # apply Alembic migrations against local DB
make gen-client       # regenerate the typed TS client from /openapi.json
```

## Layout

```
NutriRoll/
├── PROJECT_VISION.md
├── Makefile
├── docker-compose.yml
├── .github/workflows/ci.yml
├── web/      # Next.js 15 + React 19 + Tailwind v4 + shadcn + Biome + next-intl + Serwist
├── server/   # FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + Alembic, uv-managed
├── data/seed/   # human-provided seed CSVs (do not invent values)
├── tools/    # one-off scripts (seed loader, eval harness)
└── docs/adr/ # decision records
```
