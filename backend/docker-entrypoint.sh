#!/bin/sh
# Apply pending Alembic migrations, then exec the given command.
#
# Runs on every container start (design §11.1: "Migrations run on backend
# startup"). Idempotent — Alembic no-ops when the schema is already current —
# so this is safe on every restart, not just the first one.
set -e

echo "Applying database migrations..."
python -m alembic upgrade head

exec "$@"
