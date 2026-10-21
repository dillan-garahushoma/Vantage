# Install the pinned, verified portable runtime without changing system services.
$ErrorActionPreference = 'Stop'
$runtime = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '.local/postgresql'))
$version = '17.11'
$url = 'https://get.enterprisedb.com/postgresql/postgresql-17.11-1-windows-x64-binaries.zip'
$expectedHash = '6EABDF00D2893713B75DB4336A23C3FDF505F056E217EC6E2E95D901750CFEA3'
$archive = Join-Path $runtime 'postgresql-17.11-1-windows-x64-binaries.zip'
$executable = Join-Path $runtime 'pgsql/bin/postgres.exe'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
if (-not (Test-Path -LiteralPath $executable)) {
    if (-not (Test-Path -LiteralPath $archive)) {
        Write-Host 'Downloading the pinned portable PostgreSQL archive.'
        Invoke-WebRequest -Uri $url -OutFile $archive -TimeoutSec 300
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expectedHash) {
        throw 'The cached archive hash does not match; nothing was extracted or deleted.'
    }
    if (Test-Path -LiteralPath (Join-Path $runtime 'pgsql')) { throw 'A partial binaries directory exists; it was left untouched.' }
    $zip = [IO.Compression.ZipFile]::OpenRead($archive)
    try {
        foreach ($entry in $zip.Entries) {
            if ($entry.FullName -notmatch '^pgsql/(bin|lib|share)/') { continue }
            $destination = [IO.Path]::GetFullPath((Join-Path $runtime $entry.FullName))
            if (-not $destination.StartsWith($runtime + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Archive member escapes the intended local runtime directory.'
            }
            if ($entry.FullName.EndsWith('/')) { New-Item -ItemType Directory -Path $destination -Force | Out-Null; continue }
            New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($destination)) -Force | Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destination, $false)
        }
    } finally { $zip.Dispose() }
    @{version=$version; url=$url; archive_sha256=$expectedHash.ToLowerInvariant()} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'runtime-source.json')
}
& $executable --version
if ($LASTEXITCODE -ne 0) { throw 'The portable PostgreSQL executable did not run.' }
& (Join-Path $PSScriptRoot 'Local-Database.ps1') -Action Initialize
