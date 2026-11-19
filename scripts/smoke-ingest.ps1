<#
.SYNOPSIS
    Smoke test for CORS and the document upload -> ingestion -> knowledge graph path.

.DESCRIPTION
    Builds a small DOCX in memory, uploads it, and waits for ingestion to reach a
    terminal state. The first run downloads the embedding model, so allow a few
    minutes. Exits non-zero on failure. Needs a reachable backend; no LLM key.
#>
[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://localhost:8000/api/v1',
    [string]$Origin = 'http://localhost:3000',
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'
$failures = 0
function Check([string]$Name, [bool]$Ok, [string]$Detail = '') {
    if ($Ok) { Write-Host "PASS  $Name $Detail" } else { Write-Host "FAIL  $Name $Detail"; $script:failures++ }
}

# --- CORS preflight from the frontend origin
$pre = Invoke-WebRequest -Method Options -Uri "$BaseUrl/projects" -UseBasicParsing -Headers @{
    Origin = $Origin; 'Access-Control-Request-Method' = 'POST'; 'Access-Control-Request-Headers' = 'authorization,content-type'
}
$allowed = [string]$pre.Headers['Access-Control-Allow-Origin']
Check 'CORS preflight allows the frontend origin' ($allowed -eq $Origin) "($allowed)"

$evil = Invoke-WebRequest -Method Options -Uri "$BaseUrl/projects" -UseBasicParsing -Headers @{
    Origin = 'http://evil.example'; 'Access-Control-Request-Method' = 'POST'
} -SkipHttpErrorCheck
Check 'CORS preflight refuses an unknown origin' ([string]::IsNullOrEmpty([string]$evil.Headers['Access-Control-Allow-Origin'])) ''

# --- register, project
$email = "ingest$(Get-Random)@example.com"; $password = 'correct-horse-battery'
Invoke-RestMethod -Method Post -Uri "$BaseUrl/auth/register" -ContentType 'application/json' -Body (@{ email = $email; password = $password; name = 'Ingest' } | ConvertTo-Json) | Out-Null
$login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/auth/login" -ContentType 'application/json' -Body (@{ email = $email; password = $password } | ConvertTo-Json)
$auth = @{ Authorization = "Bearer $($login.data.access_token)" }
$project = Invoke-RestMethod -Method Post -Uri "$BaseUrl/projects" -Headers $auth -ContentType 'application/json' -Body (@{ title = 'Ingest project' } | ConvertTo-Json)
$projectId = $project.data.id

# --- build a small DOCX with python-docx from the backend venv
$docx = Join-Path ([IO.Path]::GetTempPath()) "aegis-smoke-$(Get-Random).docx"
$python = Join-Path $PSScriptRoot '..\backend\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = Join-Path $PSScriptRoot '../backend/.venv/bin/python' }
$code = @"
from docx import Document
d = Document()
d.add_heading('Transformers in natural language processing', 1)
d.add_paragraph('Vaswani et al. introduced the Transformer architecture in 2017. It relies on self-attention instead of recurrence. Researchers at Google and the University of Toronto showed that attention mechanisms allow models to capture long-range dependencies.')
d.add_paragraph('BERT, developed at Google, uses bidirectional training of Transformers for language understanding. GPT models from OpenAI use decoder-only Transformers for generation.')
d.save(r'$docx')
"@
& $python -c $code
Check 'built sample DOCX' (Test-Path $docx) ''

# --- upload
$uploadUri = "$BaseUrl/projects/$projectId/documents"
$form = @{ file = Get-Item $docx }
$up = Invoke-WebRequest -Method Post -Uri $uploadUri -Headers $auth -Form $form -UseBasicParsing
Check 'upload accepted' ($up.StatusCode -eq 201) "($($up.StatusCode))"
$docId = ($up.Content | ConvertFrom-Json).data.id

# --- wait for ingestion
$status = ''; $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    $doc = Invoke-RestMethod -Uri "$BaseUrl/documents/$docId" -Headers $auth
    $status = $doc.data.status
    if ($status -in 'ready', 'failed') { break }
    Start-Sleep -Seconds 5
}
Check 'document ingested' ($status -eq 'ready') "(status=$status)"
if ($status -eq 'failed') { Write-Host "INFO  error: $($doc.data.error_message)" }

# --- graph built from ingestion
$stats = Invoke-RestMethod -Uri "$BaseUrl/projects/$projectId/graph/stats" -Headers $auth
Write-Host "INFO  graph after ingestion: nodes=$($stats.data.totalNodes) edges=$($stats.data.totalEdges)"

# --- viewer-role / tenancy: a second user cannot read this project
$email2 = "other$(Get-Random)@example.com"
Invoke-RestMethod -Method Post -Uri "$BaseUrl/auth/register" -ContentType 'application/json' -Body (@{ email = $email2; password = $password; name = 'Other' } | ConvertTo-Json) | Out-Null
$login2 = Invoke-RestMethod -Method Post -Uri "$BaseUrl/auth/login" -ContentType 'application/json' -Body (@{ email = $email2; password = $password } | ConvertTo-Json)
$other = Invoke-WebRequest -Uri "$BaseUrl/projects/$projectId/documents" -Headers @{ Authorization = "Bearer $($login2.data.access_token)" } -UseBasicParsing -SkipHttpErrorCheck
Check 'another user gets 404 for this project' ($other.StatusCode -eq 404) "($($other.StatusCode))"

Remove-Item $docx -ErrorAction SilentlyContinue
if ($failures -eq 0) { Write-Host 'Ingestion smoke test passed.'; exit 0 }
Write-Host "Ingestion smoke test failed: $failures check(s)."; exit 1
