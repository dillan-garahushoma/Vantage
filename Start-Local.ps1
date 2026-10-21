param([switch]$FrontendOnly, [switch]$Migrate)

$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$frontendRoot = Join-Path $appRoot 'frontend'
$backendRoot = Join-Path $appRoot 'backend'
$runtimeRoot = Join-Path $appRoot '.local'
$nodeCommand = Get-Command node -ErrorAction Stop
$viteScript = Join-Path $frontendRoot 'node_modules/vite/bin/vite.js'

if (-not (Test-Path -LiteralPath $viteScript)) {
    throw 'Frontend dependencies are missing. Run npm ci from frontend first.'
}

if (-not $FrontendOnly) {
    $backendPython = Join-Path $backendRoot 'venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $backendPython)) {
        throw 'Create backend/venv and install backend/requirements.txt first. See HANDOFF_BACKEND.md.'
    }
    if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
        throw 'DATABASE_URL is not set. Configure your local PostgreSQL connection in this terminal. See HANDOFF_BACKEND.md. The connection value is never printed.'
    }
    if ([string]::IsNullOrWhiteSpace($env:SECRET_KEY)) {
        # Development process only: never written to disk or printed.
        $env:SECRET_KEY = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
    }
    $env:ENVIRONMENT = 'development'
    if ($Migrate) {
        Push-Location $backendRoot
        try {
            & $backendPython -m alembic -c alembic.ini upgrade head
            if ($LASTEXITCODE -ne 0) { throw 'The local database migration failed; services were not started.' }
        } finally { Pop-Location }
    }
}

$ports = if ($FrontendOnly) { @(5173) } else { @(8000, 5173) }
foreach ($port in $ports) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Stop your existing local service or run it separately; this script will not stop another process."
    }
}

New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
$processRecords = @()
if (-not $FrontendOnly) {
    $apiProcess = Start-Process -FilePath $backendPython -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeRoot 'api.log') -RedirectStandardError (Join-Path $runtimeRoot 'api-error.log') -PassThru
    $processRecords += [pscustomobject]@{ name = 'api'; pid = $apiProcess.Id; started = $apiProcess.StartTime.ToUniversalTime().ToString('o') }
}
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
$frontendProcess = Start-Process -FilePath $nodeCommand.Source -ArgumentList @($viteScript, '--host', '127.0.0.1', '--port', '5173', '--strictPort') -WorkingDirectory $frontendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeRoot 'frontend.log') -RedirectStandardError (Join-Path $runtimeRoot 'frontend-error.log') -PassThru
$processRecords += [pscustomobject]@{ name = 'frontend'; pid = $frontendProcess.Id; started = $frontendProcess.StartTime.ToUniversalTime().ToString('o') }
$processRecords | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeRoot 'processes.json')
Write-Host 'Frontend started: http://127.0.0.1:5173'
if (-not $FrontendOnly) { Write-Host 'API starting: http://127.0.0.1:8000/docs â€” check .local/api-error.log for startup readiness.' }
Write-Host 'Process IDs are recorded in .local/processes.json. Run Stop-Local.ps1 to stop only these recorded processes.'
