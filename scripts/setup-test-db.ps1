<#
.SYNOPSIS
    Create the test database for integration tests.

.DESCRIPTION
    Ensures the aegis_test database exists in the development Postgres container.
    This must be run after the Docker development stack is running.

.EXAMPLE
    pwsh ./scripts/setup-test-db.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Skip { param([string]$Message) Write-Host "    $Message" -ForegroundColor DarkGray }
function Write-Error { param([string]$Message) Write-Host "    ERROR: $Message" -ForegroundColor Red }

Write-Step 'Setting up test database'

# Check if Docker is available
try {
    docker --version | Out-Null
}
catch {
    Write-Error "Docker is not available. Please install Docker and try again."
    exit 1
}

# Check if the postgres container is running
$ContainerName = "aegis-research-os-postgres-1"
$ContainerStatus = docker inspect -f '{{.State.Status}}' $ContainerName 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Postgres container '$ContainerName' not found."
    Write-Error "Start the development stack first:"
    Write-Error "  docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml up -d"
    exit 1
}

if ($ContainerStatus -ne "running") {
    Write-Error "Postgres container '$ContainerName' is not running (status: $ContainerStatus)."
    Write-Error "Start the development stack first:"
    Write-Error "  docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml up -d"
    exit 1
}

# Check if aegis_test database already exists
$DbExists = docker exec $ContainerName psql -U aegis -d aegis -t -c "SELECT 1 FROM pg_database WHERE datname='aegis_test';" 2>$null
if ($LASTEXITCODE -eq 0 -and $DbExists.Trim() -eq "1") {
    Write-Skip "Test database 'aegis_test' already exists."
}
else {
    # Create the test database
    Write-Step "Creating test database 'aegis_test'..."
    docker exec $ContainerName psql -U aegis -d aegis -c "CREATE DATABASE aegis_test;"
    if ($LASTEXITCODE -eq 0) {
        Write-Skip "Test database 'aegis_test' created successfully."
    }
    else {
        Write-Error "Failed to create test database."
        exit 1
    }
}

Write-Step 'Test database setup complete'
Write-Host "    Integration tests can now run with: pytest tests/integration/" -ForegroundColor Green