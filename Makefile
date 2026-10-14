.PHONY: install test test-cov lint run serve docker-up docker-down clean

install:
	uv venv .venv --python 3.12
	uv pip install --python .venv -e ".[dev]"

test:
	uv run pytest

test-cov:
	uv run pytest --cov=devswarm --cov-report=term-missing

run:
	uv run devswarm run "$(TASK)"

serve:
	uv run devswarm serve --reload

status:
	uv run devswarm status

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .coverage htmlcov .devswarm *.sqlite3 devswarm.db
