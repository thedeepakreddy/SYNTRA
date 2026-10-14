# ==============================================================================
# SYNTRA Project Automation Makefile
# Synchronized Intelligence for Autonomous Engineering
# ==============================================================================

.PHONY: help bootstrap doctor up down test test-all test-cov lint typecheck smoke-test clean run serve status migrate

help:
	@echo "SYNTRA Automation Commands:"
	@echo "  make bootstrap   - Idempotently bootstrap local Python workspace and dependencies"
	@echo "  make doctor      - Run comprehensive system diagnostics and prerequisite checks"
	@echo "  make up          - Start containerized services (PostgreSQL, Redis, MinIO) via Compose"
	@echo "  make down        - Stop containerized infrastructure services"
	@echo "  make migrate     - Run Alembic database migrations to upgrade schema to head"
	@echo "  make test        - Run fast unit and contract test suites"
	@echo "  make test-cov    - Run test suite with line-level coverage reporting"
	@echo "  make lint        - Run ruff code formatter and linter checks"
	@echo "  make typecheck   - Run mypy strict static type analysis"
	@echo "  make smoke-test  - Run end-to-end smoke test sanity suite"
	@echo "  make serve       - Run FastAPI control plane server in development mode"
	@echo "  make clean       - Remove test caches, temporary files, and sandbox runtimes"

bootstrap:
	bash scripts/bootstrap.sh

doctor:
	bash scripts/doctor.sh

up:
	docker compose up -d

down:
	docker compose down

migrate:
	uv run alembic upgrade head

test:
	uv run pytest tests/unit tests/security tests/test_domain_and_persistence.py tests/test_migrations.py tests/test_phase1_initialization.py

test-all:
	uv run pytest

test-cov:
	uv run pytest --cov=syntra --cov-report=term-missing

lint:
	uv run ruff check .

typecheck:
	uv run mypy src/syntra

smoke-test:
	bash scripts/smoke-test.sh

run:
	uv run syntra run "$(TASK)"

serve:
	uv run syntra serve --reload

status:
	uv run syntra status

clean:
	rm -rf .pytest_cache .coverage htmlcov .syntra/sandboxes/* *.sqlite3
	find . -type d -name "__pycache__" -exec rm -rf {} +
