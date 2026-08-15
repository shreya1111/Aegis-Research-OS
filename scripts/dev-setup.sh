#!/usr/bin/env bash
# Prepare a local development environment (Linux / macOS).
# Idempotent: safe to re-run.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
ENV_EXAMPLE="${REPO_ROOT}/deployment/.env.example"

step() { printf '\n==> %s\n' "$1"; }
note() { printf '    %s\n' "$1"; }

step 'Configuration'
if [[ -f "${ENV_FILE}" ]]; then
  note '.env already exists; leaving it untouched.'
else
  cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  note '.env created from deployment/.env.example — set POSTGRES_PASSWORD before starting Docker.'
fi

step 'Backend (Python virtual environment)'
cd "${REPO_ROOT}/backend"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
else
  note 'Virtual environment already present.'
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check --upgrade pip
.venv/bin/python -m pip install --quiet --disable-pip-version-check -e '.[dev]'
note 'Backend dependencies installed.'
note 'Integration tests require a running Postgres with an "aegis_test" database.'
note 'After starting the dev stack, create it once with:'
note '  docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml exec postgres psql -U aegis -d aegis -c "CREATE DATABASE aegis_test"'

step 'Frontend (npm dependencies)'
cd "${REPO_ROOT}/frontend"
npm install --no-fund --no-audit
note 'Frontend dependencies installed.'

step 'Done'
cat <<'EOF'
Next steps:
  Full stack    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml up
  Backend only  backend/.venv/bin/python -m uvicorn app.main:app --reload   (run from backend/)
  Frontend only npm run dev                                                 (run from frontend/)
  Verify        ./scripts/verify.sh
EOF
