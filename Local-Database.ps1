param(
    [ValidateSet('Initialize', 'Start', 'Stop', 'Use', 'Test', 'Migrate')]
    [string]$Action = 'Use',
    [ValidateSet('Development', 'Test', 'MigrationTest')]
    [string]$Database = 'Development'
)

$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.local/postgresql'
$bin = Join-Path $runtime 'pgsql/bin'
$cluster = Join-Path $runtime 'data'
$port = 54329
$backend = Join-Path $PSScriptRoot 'backend'
$python = Join-Path $backend 'venv/Scripts/python.exe'
$names = @{ Development = 'valora_local_dev'; Test = 'valora_acceptance_demo_test'; MigrationTest = 'valora_migration_test' }
$accounts = @{ Development = 'valora_dev_user'; Test = 'valora_test_user'; MigrationTest = 'valora_test_user' }

function Invoke-LocalNative {
    param([string]$Executable, [string[]]$Arguments, [string]$InputText, [hashtable]$Environment = @{})
    $info = [Diagnostics.ProcessStartInfo]::new($Executable)
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.WindowStyle = 'Hidden'
    $info.RedirectStandardInput = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    foreach ($key in $Environment.Keys) { $info.Environment[$key] = $Environment[$key] }
    $process = [Diagnostics.Process]::Start($info)
    $output = $process.StandardOutput.ReadToEndAsync()
    $errors = $process.StandardError.ReadToEndAsync()
    if ($InputText) { $process.StandardInput.Write($InputText) }
    $process.StandardInput.Close()
    if (-not $process.WaitForExit(60000)) { throw 'Local database helper timed out; inspect the local PostgreSQL server log.' }
    if ([IO.Path]::GetFileName($Executable) -eq 'pg_ctl.exe' -and $process.ExitCode -eq 0) {
        # The detached Windows server may retain inherited pipe handles after
        # pg_ctl exits. Never wait for server-lifetime EOF on those handles.
        $process.Dispose()
        return ''
    }
    $captured = $output.GetAwaiter().GetResult()
    $diagnostic = $errors.GetAwaiter().GetResult()
    if ($process.ExitCode -ne 0) {
        # SQL/bootstrap errors could contain a generated credential: never emit them.
        if ([IO.Path]::GetFileName($Executable) -ne 'psql.exe') {
            if ($InputText) { $diagnostic = $diagnostic.Replace($InputText.Trim(), '[redacted]') }
            throw "Local database helper failed: $([IO.Path]::GetFileName($Executable)) (exit $($process.ExitCode)): $diagnostic"
        }
        throw "Local database SQL helper failed (exit $($process.ExitCode)); credentials and SQL text withheld."
    }
    return $captured.Trim()
}

function Get-LocalCredential([string]$Name, [switch]$Create) {
    $file = Join-Path $runtime "$Name.credential.xml"
    if (Test-Path -LiteralPath $file) { return Import-Clixml -LiteralPath $file }
    if (-not $Create) { throw 'Local credentials are missing. Run Local-Database.ps1 -Action Initialize first.' }
    $generated = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
    $secure = ConvertTo-SecureString -String $generated -AsPlainText -Force
    $credential = [pscredential]::new($Name, $secure)
    $credential | Export-Clixml -LiteralPath $file
    return $credential
}

function Invoke-LocalPython([string[]]$Arguments) {
    $info = [Diagnostics.ProcessStartInfo]::new($python)
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.WindowStyle = 'Hidden'
    $info.WorkingDirectory = $backend
    $info.Environment['PYTHONIOENCODING'] = 'utf-8'
    $info.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
    $info.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::Start($info)
    $output = $process.StandardOutput.ReadToEndAsync()
    $errors = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $safe = $output.GetAwaiter().GetResult() + $errors.GetAwaiter().GetResult()
    $safe = [regex]::Replace($safe, '(postgresql(?:\+\w+)?://[^:\s]+:)[^@\s]+@', '$1[redacted]@')
    $safe = [regex]::Replace($safe, 'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[bearer token redacted]')
    if ($env:SECRET_KEY) { $safe = $safe.Replace($env:SECRET_KEY, '[redacted]') }
    Write-Host $safe
    if ($process.ExitCode -ne 0) { throw 'Database acceptance command failed; inspect the sanitized test/migration result.' }
}

function Start-LocalPostgres {
    if (-not (Test-Path -LiteralPath (Join-Path $cluster 'PG_VERSION'))) { throw 'Cluster missing. Run -Action Initialize.' }
    $info = [Diagnostics.ProcessStartInfo]::new((Join-Path $bin 'pg_ctl.exe'))
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($arg in @('status', '-D', $cluster)) { $info.ArgumentList.Add($arg) }
    $check = [Diagnostics.Process]::Start($info)
    $null = $check.StandardOutput.ReadToEnd()
    $null = $check.StandardError.ReadToEnd()
    $check.WaitForExit()
    if ($check.ExitCode -eq 0) { return }
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port belongs to another process; nothing was stopped." }
    $null = Invoke-LocalNative -Executable (Join-Path $bin 'pg_ctl.exe') -Arguments @('start', '-D', $cluster, '-l', (Join-Path $runtime 'server.log'), '-w', '-t', '45')
}

if (-not (Test-Path -LiteralPath (Join-Path $bin 'postgres.exe'))) {
    throw 'Portable PostgreSQL binaries are missing under .local/postgresql/pgsql. See LOCAL_DATABASE.md.'
}

if ($Action -eq 'Initialize') {
    New-Item -ItemType Directory -Path $runtime -Force | Out-Null
    $admin = Get-LocalCredential 'valora_local_admin' -Create
    if (-not (Test-Path -LiteralPath (Join-Path $cluster 'PG_VERSION'))) {
        if (Test-Path -LiteralPath $cluster) { throw 'An incomplete cluster directory exists; it was left untouched.' }
        # Windows initdb requires a file rather than stdin. This private,
        # generated password file exists only during initialization.
        $passwordFile = Join-Path $runtime '.init-password.tmp'
        if (Test-Path -LiteralPath $passwordFile) { throw 'A temporary initialization file already exists; it was left untouched.' }
        try {
            [IO.File]::WriteAllText($passwordFile, $admin.GetNetworkCredential().Password + "`n", [Text.UTF8Encoding]::new($false))
            $acl = Get-Acl -LiteralPath $passwordFile
            $acl.SetAccessRuleProtection($true, $false)
            $rule = [Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.WindowsIdentity]::GetCurrent().User, 'FullControl', 'Allow')
            $acl.AddAccessRule($rule)
            Set-Acl -LiteralPath $passwordFile -AclObject $acl
            $null = Invoke-LocalNative -Executable (Join-Path $bin 'initdb.exe') -Arguments @('-D', $cluster, '-U', $admin.UserName, '--encoding=UTF8', '--locale=C', '--auth-host=scram-sha-256', '--auth-local=scram-sha-256', "--pwfile=$passwordFile")
        } finally {
            if (Test-Path -LiteralPath $passwordFile) { Remove-Item -LiteralPath $passwordFile }
        }
        Add-Content -LiteralPath (Join-Path $cluster 'postgresql.conf') -Value "`nlisten_addresses = '127.0.0.1'`nport = $port`n"
    }
    Start-LocalPostgres
    $psql = Join-Path $bin 'psql.exe'
    $arguments = @('-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-h', '127.0.0.1', '-p', "$port", '-U', $admin.UserName, '-d', 'postgres')
    $adminEnvironment = @{ PGPASSWORD = $admin.GetNetworkCredential().Password }
    foreach ($role in @('valora_dev_user', 'valora_test_user')) {
        $credential = Get-LocalCredential $role -Create
        $exists = Invoke-LocalNative -Executable $psql -Arguments $arguments -Environment $adminEnvironment -InputText "SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname = '$role');"
        if ($exists -eq 'f') {
            $passwordLiteral = $credential.GetNetworkCredential().Password.Replace("'", "''")
            $null = Invoke-LocalNative -Executable $psql -Arguments $arguments -Environment $adminEnvironment -InputText "CREATE ROLE $role LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '$passwordLiteral';"
        }
    }
    foreach ($kind in @('Development', 'Test', 'MigrationTest')) {
        $name = $names[$kind]
        $owner = $accounts[$kind]
        $exists = Invoke-LocalNative -Executable $psql -Arguments $arguments -Environment $adminEnvironment -InputText "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = '$name');"
        if ($exists -eq 'f') {
            $null = Invoke-LocalNative -Executable $psql -Arguments $arguments -Environment $adminEnvironment -InputText "CREATE DATABASE $name OWNER $owner;"
            $null = Invoke-LocalNative -Executable $psql -Arguments $arguments -Environment $adminEnvironment -InputText "REVOKE CONNECT ON DATABASE $name FROM PUBLIC; GRANT CONNECT ON DATABASE $name TO $owner;"
        }
    }
    Write-Host 'Local PostgreSQL initialized on 127.0.0.1:54329. Separate development and test databases are ready.'
    return
}

if ($Action -eq 'Start') { Start-LocalPostgres; Write-Host 'Local PostgreSQL is running on 127.0.0.1:54329.'; return }
if ($Action -eq 'Stop') {
    $null = Invoke-LocalNative -Executable (Join-Path $bin 'pg_ctl.exe') -Arguments @('stop', '-D', $cluster, '-m', 'fast', '-w', '-t', '45')
    Write-Host 'Stopped this workspace PostgreSQL cluster.'
    return
}

Start-LocalPostgres
if ($Action -eq 'Test') { $Database = 'Test' }
$credential = Get-LocalCredential $accounts[$Database]
$encoded = [uri]::EscapeDataString($credential.GetNetworkCredential().Password)
$env:DATABASE_URL = "postgresql+asyncpg://$($credential.UserName):$encoded@127.0.0.1:$port/$($names[$Database])"
if ($Database -eq 'Development') { Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue }
else { $env:TEST_DATABASE_URL = $env:DATABASE_URL }
if (-not $env:SECRET_KEY) { $env:SECRET_KEY = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(48)) }
$env:ENVIRONMENT = 'development'
Write-Host "Configured $Database database: $($names[$Database]) on 127.0.0.1:$port (credentials hidden)."
if ($Action -in @('Test', 'Migrate')) {
    Push-Location $backend
    try {
        if ($Action -eq 'Test') { Invoke-LocalPython -Arguments @('-m', 'pytest', 'tests', '-q', '--tb=short') }
        else { Invoke-LocalPython -Arguments @('-m', 'alembic', '-c', 'alembic.ini', 'upgrade', 'head') }
    } finally { Pop-Location }
}
