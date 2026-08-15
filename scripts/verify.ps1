<#
.SYNOPSIS
    Run every quality gate locally, in the same order as CI.

.DESCRIPTION
    Lint, format check, type check, and tests for both workspaces. Exits non-zero
    on the first failure so it can be wired into a pre-push hook.

.EXAMPLE
    pwsh ./scripts/verify.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot 'backend'
$FrontendDir = Join-Path $RepoRoot 'frontend'
$VenvPython = Join-Path $BackendDir '.venv/Scripts/python.exe'

function Invoke-Gate {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [Parameter(Mandatory)][scriptblock]$Action
    )

    Write-Host "==> $Name" -ForegroundColor Cyan
    Push-Location $WorkingDirectory
    try {
        & $Action
        if ($LASTEXITCODE -ne 0) {
            throw "$Name failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $VenvPython)) {
    throw 'Backend virtual environment not found. Run scripts/dev-setup.ps1 first.'
}

Invoke-Gate 'backend · ruff check' $BackendDir { & $VenvPython -m ruff check . }
Invoke-Gate 'backend · ruff format' $BackendDir { & $VenvPython -m ruff format --check . }
Invoke-Gate 'backend · mypy' $BackendDir { & $VenvPython -m mypy app tests }
Invoke-Gate 'backend · pytest' $BackendDir { & $VenvPython -m pytest -q }

Invoke-Gate 'frontend · prettier' $FrontendDir { npm run format:check }
Invoke-Gate 'frontend · eslint' $FrontendDir { npm run lint }
Invoke-Gate 'frontend · tsc' $FrontendDir { npm run type-check }
Invoke-Gate 'frontend · vitest' $FrontendDir { npm run test }

Write-Host "`nAll quality gates passed." -ForegroundColor Green
