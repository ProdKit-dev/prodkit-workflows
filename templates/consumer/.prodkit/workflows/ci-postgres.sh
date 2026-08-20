#!/usr/bin/env bash
set -euo pipefail
: "${PRODKIT_POSTGRES_HOST:?}" "${PRODKIT_POSTGRES_PORT:?}"
export DATABASE_URL="postgresql+psycopg://$PRODKIT_POSTGRES_USER:$PRODKIT_POSTGRES_PASSWORD@$PRODKIT_POSTGRES_HOST:$PRODKIT_POSTGRES_PORT/$PRODKIT_POSTGRES_DATABASE"
# Example: uv run alembic upgrade head && uv run pytest tests/postgres -ra
