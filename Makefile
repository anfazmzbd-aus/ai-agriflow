.PHONY: install test lint format typecheck docs serve-docs all

install:
	uv sync --extra dev

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy

docs:
	uv run mkdocs build

serve-docs:
	uv run mkdocs serve

all: lint typecheck test docs
