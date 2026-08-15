#!/usr/bin/env bash
# Run every quality gate locally, in the same order as CI.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"
VENV_PYTHON="${BACKEND_DIR}/.venv/bin/python"

gate() { printf '\n==> %s\n' "$1"; }

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo 'Backend virtual environment not found. Run scripts/dev-setup.sh first.' >&2
  exit 1
fi

cd "${BACKEND_DIR}"
gate 'backend · ruff check'; "${VENV_PYTHON}" -m ruff check .
gate 'backend · ruff format'; "${VENV_PYTHON}" -m ruff format --check .
gate 'backend · mypy'; "${VENV_PYTHON}" -m mypy app tests
gate 'backend · pytest'; "${VENV_PYTHON}" -m pytest -q

cd "${FRONTEND_DIR}"
gate 'frontend · prettier'; npm run format:check
gate 'frontend · eslint'; npm run lint
gate 'frontend · tsc'; npm run type-check
gate 'frontend · vitest'; npm run test

printf '\nAll quality gates passed.\n'
