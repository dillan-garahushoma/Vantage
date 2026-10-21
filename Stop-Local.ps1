$ErrorActionPreference = 'Stop'
$recordPath = Join-Path $PSScriptRoot '.local/processes.json'
if (-not (Test-Path -LiteralPath $recordPath)) { Write-Host 'No local launcher process record exists.'; return }
$records = @(Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json)
foreach ($record in $records) {
    $process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
    if (-not $process) { continue }
    if ($process.StartTime.ToUniversalTime().ToString('o') -ne $record.started) {
        Write-Warning "Skipping reused process ID $($record.pid)."
        continue
    }
    Stop-Process -Id $process.Id
    Write-Host "Stopped $($record.name)."
}
