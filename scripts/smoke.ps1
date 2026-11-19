<#
.SYNOPSIS
    End-to-end API smoke test against a running backend.

.DESCRIPTION
    Registers a throwaway user and walks the main flows: auth, projects, reports,
    export, usage, activity, graph, and the unauthenticated rejection.
    Exits non-zero if any check fails. Needs only a reachable backend; no LLM key.

.PARAMETER BaseUrl
    API root. Defaults to the local dev backend.
#>
[CmdletBinding()]
param([string]$BaseUrl = 'http://localhost:8000/api/v1')

$ErrorActionPreference = 'Stop'
$script:Failures = 0

function Check {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    if ($Ok) { Write-Host "PASS  $Name $Detail" } else { Write-Host "FAIL  $Name $Detail"; $script:Failures++ }
}

function Invoke-Api {
    param([string]$Method, [string]$Path, $Body = $null, [string]$Token = $null)
    $headers = @{}
    if ($Token) { $headers['Authorization'] = "Bearer $Token" }
    $params = @{ Method = $Method; Uri = "$BaseUrl$Path"; Headers = $headers; UseBasicParsing = $true }
    if ($null -ne $Body) { $params['Body'] = ($Body | ConvertTo-Json -Depth 5); $params['ContentType'] = 'application/json' }
    try {
        $response = Invoke-WebRequest @params
        return [pscustomobject]@{ Code = [int]$response.StatusCode; Json = ($response.Content | ConvertFrom-Json); Response = $response }
    }
    catch {
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        return [pscustomobject]@{ Code = $code; Json = $null; Response = $null }
    }
}

$email = "smoke$(Get-Random)@example.com"
$password = 'correct-horse-battery'

$r = Invoke-Api POST '/auth/register' @{ email = $email; password = $password; name = 'Smoke' }
Check 'register' ($r.Code -eq 201) "($($r.Code))"

$r = Invoke-Api POST '/auth/login' @{ email = $email; password = $password }
Check 'login' ($r.Code -eq 200) "($($r.Code))"
$token = $r.Json.data.access_token

$r = Invoke-Api POST '/auth/login' @{ email = $email; password = 'wrong-password-123' }
Check 'login with wrong password is rejected' ($r.Code -eq 401) "($($r.Code))"

$r = Invoke-Api GET '/auth/me' -Token $token
Check 'current user' ($r.Code -eq 200 -and $r.Json.data.email -eq $email) "($($r.Code))"

$r = Invoke-Api POST '/projects' @{ title = 'Smoke project' } $token
Check 'create project' ($r.Code -eq 201) "($($r.Code))"
$projectId = $r.Json.data.id

$r = Invoke-Api GET '/projects' -Token $token
Check 'list projects' ($r.Code -eq 200 -and $r.Json.data.total -eq 1) "(total=$($r.Json.data.total))"

$r = Invoke-Api POST "/projects/$projectId/reports" @{ type = 'literature_review'; title = 'Smoke review' } $token
Check 'create report' ($r.Code -eq 201) "($($r.Code))"
$reportId = $r.Json.data.id

# The generation runs as a background task; poll briefly for completion.
$status = ''
for ($i = 0; $i -lt 20; $i++) {
    $r = Invoke-Api GET "/reports/$reportId" -Token $token
    $status = $r.Json.data.status
    if ($status -in 'completed', 'failed') { break }
    Start-Sleep -Milliseconds 500
}
Check 'report generated' ($status -eq 'completed') "(status=$status)"

foreach ($format in 'markdown', 'html', 'latex', 'docx') {
    try {
        $x = Invoke-WebRequest -Uri "$BaseUrl/reports/$reportId/export?format=$format" -Headers @{ Authorization = "Bearer $token" } -UseBasicParsing
        Check "export $format" ($x.StatusCode -eq 200 -and $x.RawContentLength -gt 0) "($($x.Headers['Content-Type']), $($x.RawContentLength) bytes)"
    }
    catch { Check "export $format" $false $_.Exception.Message }
}

foreach ($path in "/projects/$projectId/usage", "/projects/$projectId/activity", "/projects/$projectId/graph/data", "/projects/$projectId/graph/stats", "/projects/$projectId/documents", "/projects/$projectId/members") {
    $r = Invoke-Api GET $path -Token $token
    Check "GET $path" ($r.Code -eq 200) "($($r.Code))"
}

$r = Invoke-Api GET '/projects'
Check 'unauthenticated request is rejected' ($r.Code -eq 401) "($($r.Code))"

$r = Invoke-Api POST "/projects/$projectId/query" @{ question = 'What is this project about?' } $token
Write-Host "INFO  query without LLM key -> HTTP $($r.Code) (a clean error is expected, not a crash)"
Check 'query does not crash the server (no 5xx other than provider error)' ($r.Code -ne 500) "($($r.Code))"

Write-Host ''
if ($script:Failures -eq 0) { Write-Host 'Smoke test passed.'; exit 0 }
Write-Host "Smoke test failed: $script:Failures check(s)."; exit 1
