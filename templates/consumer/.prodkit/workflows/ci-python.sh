#!/usr/bin/env bash
set -euo pipefail
: "${PRODKIT_PYTHON_VERSION:?}"
uv sync --all-packages --all-groups --locked --python "$PRODKIT_PYTHON_VERSION"
uv run --python "$PRODKIT_PYTHON_VERSION" --no-sync ruff format --check .
uv run --python "$PRODKIT_PYTHON_VERSION" --no-sync ruff check .
if [ "$PRODKIT_PYTHON_VERSION" = "3.12" ]; then uv run --python "$PRODKIT_PYTHON_VERSION" --no-sync pyright; fi
uv run --python "$PRODKIT_PYTHON_VERSION" --no-sync pytest --cov --cov-report=term-missing --cov-fail-under=90
