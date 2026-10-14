.PHONY: bootstrap doctor smoke-test install test test-cov run serve status compose-up compose-down docker-up docker-down clean

bootstrap:
	bash scripts/bootstrap.sh

doctor:
	bash scripts/doctor.sh

smoke-test:
	bash scripts/smoke-test.sh

install:
	uv pip install -e ".[dev]"

test:
	uv run pytest

test-cov:
	uv run pytest --cov=syntra --cov-report=term-missing

run:
	uv run syntra run "$(TASK)"

serve:
	uv run syntra serve --reload

status:
	uv run syntra status

compose-up:
	docker compose up -d

compose-down:
	docker compose down

docker-up: compose-up

docker-down: compose-down

clean:
	rm -rf .pytest_cache .coverage htmlcov .syntra/sandboxes/* *.sqlite3
	find . -type d -name "__pycache__" -exec rm -rf {} +
