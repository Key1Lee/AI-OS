[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('start', 'stop', 'status', 'smoke', 'backup', 'restore', 'update')]
    [string]$Command = 'status',

    [string]$Path
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$DataDir = Join-Path $RepoRoot 'n8n\data'
$EnvFile = Join-Path $RepoRoot '.env'
$WorkflowFile = '/workflows/ai-os-example.json'
$WorkflowId = 'ai-os-local-smoke'

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments)][string[]]$Arguments)
    & docker compose --project-directory $RepoRoot @Arguments
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed: $($Arguments -join ' ')" }
}

function Initialize-LocalConfig {
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        $bytes = [byte[]]::new(32)
        $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        $key = ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
        [IO.File]::WriteAllText($EnvFile, "N8N_ENCRYPTION_KEY=$key`n", [Text.UTF8Encoding]::new($false))
        Write-Host 'Created local gitignored .env with a random encryption key.'
    }
}

function Wait-N8nHealthy {
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        $health = & docker inspect --format '{{.State.Health.Status}}' ai-os-n8n 2>$null
        if ($LASTEXITCODE -eq 0 -and $health -eq 'healthy') { return }
        Start-Sleep -Seconds 2
    }
    throw 'n8n did not become healthy within 60 seconds.'
}

function Backup-N8n {
    $backupDir = Join-Path $RepoRoot 'backups'
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    $destination = if ($Path) { [IO.Path]::GetFullPath((Join-Path $RepoRoot $Path)) } else { Join-Path $backupDir ("n8n-{0}.zip" -f (Get-Date -Format 'yyyyMMdd-HHmmss')) }
    Invoke-Compose -Arguments @('stop', 'n8n')
    try {
        if (Test-Path -LiteralPath $DataDir) {
            Compress-Archive -LiteralPath $DataDir -DestinationPath $destination -Force
        }
    }
    finally {
        Invoke-Compose -Arguments @('up', '-d', 'n8n')
        Wait-N8nHealthy
    }
    Write-Host "Backup: $destination"
}

Push-Location $RepoRoot
try {
    switch ($Command) {
        'start' {
            Initialize-LocalConfig
            Invoke-Compose -Arguments @('up', '-d', 'n8n')
            Wait-N8nHealthy
            Write-Host 'n8n: http://127.0.0.1:5678'
        }
        'stop' { Invoke-Compose -Arguments @('down') }
        'status' { Invoke-Compose -Arguments @('ps') }
        'smoke' {
            Initialize-LocalConfig
            Invoke-Compose -Arguments @('up', '-d', 'n8n')
            Wait-N8nHealthy
            Invoke-Compose -Arguments @('exec', '-T', '-e', 'N8N_RUNNERS_BROKER_PORT=5689', 'n8n', 'n8n', 'import:workflow', "--input=$WorkflowFile")
            Invoke-Compose -Arguments @('exec', '-T', '-e', 'N8N_RUNNERS_BROKER_PORT=5689', 'n8n', 'n8n', 'execute', "--id=$WorkflowId", '--rawOutput')
        }
        'backup' {
            Initialize-LocalConfig
            Backup-N8n
        }
        'restore' {
            if (-not $Path) { throw 'restore requires -Path <backup.zip>' }
            $source = [IO.Path]::GetFullPath((Join-Path $RepoRoot $Path))
            if (-not (Test-Path -LiteralPath $source)) { throw "Backup not found: $source" }
            Initialize-LocalConfig
            Invoke-Compose -Arguments @('down')
            if (Test-Path -LiteralPath $DataDir) { Remove-Item -LiteralPath $DataDir -Recurse -Force }
            Expand-Archive -LiteralPath $source -DestinationPath (Split-Path -Parent $DataDir) -Force
            Invoke-Compose -Arguments @('up', '-d', 'n8n')
            Wait-N8nHealthy
        }
        'update' {
            Initialize-LocalConfig
            Backup-N8n
            Invoke-Compose -Arguments @('pull', 'n8n')
            Invoke-Compose -Arguments @('up', '-d', 'n8n')
            Wait-N8nHealthy
        }
    }
}
finally {
    Pop-Location
}
