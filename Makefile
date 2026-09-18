.PHONY: help lint test

help:  # Show help for each of the Makefile recipes
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m: $$(echo $$l | cut -f 2- -d'#')\n"; done

lint:  # Run code lint with ruff and mypy
	uv run ruff format .
	uv run ruff check --fix .
	uv run mypy

test:  # Run the complete test suite
	uv run pytest -vv
