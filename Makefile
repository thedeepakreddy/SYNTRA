.PHONY: install test test-cov lint run serve status docker-up docker-down clean

install:
	uv venv .venv --python 3.12
	uv pip install --python .venv -e ".[dev]"

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

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .coverage htmlcov .syntra .devswarm *.sqlite3 syntra.db devswarm.db
