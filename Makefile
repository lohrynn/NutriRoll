# Makefile — top-level orchestration for NutriRoll
# All targets are local-reversible. Anything that touches shared infra must
# be invoked explicitly with confirmation (not via these targets).

SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE ?= docker compose
SERVER_DIR := server
WEB_DIR := web

.PHONY: help dev down logs check test lint typecheck fmt seed migrate \
        gen-openapi gen-client server-shell web-shell db-shell clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------- dev orchestration ----------

dev: ## Start postgres + backend + frontend via docker compose
	$(COMPOSE) up --build

down: ## Stop the dev stack
	$(COMPOSE) down

logs: ## Tail logs of the dev stack
	$(COMPOSE) logs -f --tail=200

# ---------- quality gates ----------

check: lint typecheck test ## Lint + typecheck + test (server & web)

lint: ## Run linters on both projects
	cd $(SERVER_DIR) && uv run ruff check .
	cd $(WEB_DIR) && pnpm biome check .

typecheck: ## Strict type checking on both projects
	cd $(SERVER_DIR) && uv run pyright
	cd $(WEB_DIR) && pnpm typecheck

fmt: ## Format both projects
	cd $(SERVER_DIR) && uv run ruff format .
	cd $(WEB_DIR) && pnpm biome format --write .

test: ## Unit tests on both projects
	cd $(SERVER_DIR) && uv run pytest
	cd $(WEB_DIR) && pnpm test

# ---------- database ----------

migrate: ## Apply Alembic migrations against the local DB
	cd $(SERVER_DIR) && uv run alembic upgrade head

seed: ## Load curated seed data from data/seed/ (Phase 1+)
	cd $(SERVER_DIR) && uv run python ../tools/seed/load.py

# ---------- API contract ----------

gen-openapi: ## Dump openapi.json from the FastAPI app to web/lib/api/openapi.json
	cd $(SERVER_DIR) && uv run python -m nutriroll.tools.dump_openapi \
		> ../$(WEB_DIR)/lib/api/openapi.json

gen-client: gen-openapi ## Regenerate the typed TS client from the OpenAPI spec
	cd $(WEB_DIR) && pnpm gen:client

# ---------- shells ----------

server-shell: ## Open a shell inside the running backend container
	$(COMPOSE) exec backend bash

web-shell: ## Open a shell inside the running frontend container
	$(COMPOSE) exec frontend sh

db-shell: ## psql into the dev database
	$(COMPOSE) exec postgres psql -U nutriroll -d nutriroll

# ---------- housekeeping ----------

clean: ## Remove build artifacts, caches, and node_modules
	rm -rf $(WEB_DIR)/node_modules $(WEB_DIR)/.next $(WEB_DIR)/.turbo
	rm -rf $(SERVER_DIR)/.venv $(SERVER_DIR)/.pytest_cache $(SERVER_DIR)/.ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
