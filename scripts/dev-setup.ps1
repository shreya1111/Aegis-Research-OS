<#
.SYNOPSIS
    Prepare a local development environment (Windows / PowerShell).

.DESCRIPTION
    Creates .env from the documented contract, provisions the backend virtual
    environment, and installs frontend dependencies. Idempotent: safe to re-run.

.EXAMPLE
    pwsh ./scripts/dev-setup.ps1
#>

[CmdletBinding()]
param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RepoRoot '.env'
$EnvExample = Join-Path $RepoRoot 'deployment/.env.example'

function Write-Step { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Skip { param([string]$Message) Write-Host "    $Message" -ForegroundColor DarkGray }

# --- Configuration ----------------------------------------------------------
Write-Step 'Configuration'
if (Test-Path $EnvFile) {
    Write-Skip '.env already exists; leaving it untouched.'
}
else {
    Copy-Item $EnvExample $EnvFile
    Write-Skip ".env created from deployment/.env.example — set POSTGRES_PASSWORD before starting Docker."
}

# --- Backend ----------------------------------------------------------------
if (-not $SkipBackend) {
    Write-Step 'Backend (Python virtual environment)'
    $BackendDir = Join-Path $RepoRoot 'backend'
    $VenvPython = Join-Path $BackendDir '.venv/Scripts/python.exe'

    if (-not (Test-Path $VenvPython)) {
        python -m venv (Join-Path $BackendDir '.venv')
    }
    else {
        Write-Skip 'Virtual environment already present.'
    }

    & $VenvPython -m pip install --quiet --disable-pip-version-check --upgrade pip
    Push-Location $BackendDir
    try {
        & $VenvPython -m pip install --quiet --disable-pip-version-check -e '.[dev]'
    }
    finally {
        Pop-Location
    }
    Write-Skip 'Backend dependencies installed.'
    Write-Skip 'Integration tests require a running Postgres with an "aegis_test" database.'
    Write-Skip 'After starting the dev stack, create it once with:'
    Write-Skip '  docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml exec postgres psql -U aegis -d aegis -c "CREATE DATABASE aegis_test"'
}

# --- Frontend ---------------------------------------------------------------
if (-not $SkipFrontend) {
    Write-Step 'Frontend (npm dependencies)'
    Push-Location (Join-Path $RepoRoot 'frontend')
    try {
        npm install --no-fund --no-audit
    }
    finally {
        Pop-Location
    }
    Write-Skip 'Frontend dependencies installed.'
}

Write-Step 'Done'
Write-Host @'
Next steps:
  Full stack   docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml up
  Backend only backend/.venv/Scripts/python.exe -m uvicorn app.main:app --reload   (run from backend/)
  Frontend only npm run dev                                                        (run from frontend/)
  Verify       pwsh ./scripts/verify.ps1
'@
