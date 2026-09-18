param(
    [string]$ConfigPath = (Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "KnowledgeCore\console-v1\console.env")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "KC console config not found: $ConfigPath"
}

$Settings = @{}
foreach ($RawLine in (Get-Content -LiteralPath $ConfigPath)) {
    $Line = $RawLine.Trim()
    if (-not $Line -or $Line.StartsWith("#")) {
        continue
    }
    $Equals = $Line.IndexOf("=")
    if ($Equals -lt 1) {
        throw "Invalid KC console config line."
    }
    $Settings[$Line.Substring(0, $Equals).Trim()] = $Line.Substring($Equals + 1)
}

foreach ($Required in @(
    "KNOWLEDGE_CORE_DATABASE_URL",
    "KNOWLEDGE_CORE_ARTIFACT_ROOT",
    "KNOWLEDGE_CORE_BOOTSTRAP_KEY",
    "KNOWLEDGE_CORE_BIND_HOST",
    "KNOWLEDGE_CORE_PORT",
    "KNOWLEDGE_CORE_CONSOLE_ENABLED",
    "KNOWLEDGE_CORE_CONSOLE_KEY",
    "KNOWLEDGE_CORE_CONSOLE_PROJECTS",
    "KNOWLEDGE_CORE_CONSOLE_DEFAULT_PROJECT",
    "KNOWLEDGE_CORE_POSTGRES_CONTAINER"
)) {
    if (-not $Settings.ContainsKey($Required) -or -not $Settings[$Required]) {
        throw "Required KC console config key is missing: $Required"
    }
}

if ($Settings["KNOWLEDGE_CORE_BIND_HOST"] -ne "127.0.0.1") {
    throw "C07 migration helper requires loopback-only KC binding."
}

foreach ($Name in $Settings.Keys) {
    if ($Name -eq "KNOWLEDGE_CORE_POSTGRES_CONTAINER") {
        continue
    }
    Set-Item -Path "Env:$Name" -Value $Settings[$Name]
}

$KCDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Python = Join-Path $KCDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "KC deployment virtual environment is missing: $Python"
}

$Docker = Get-Command docker.exe -CommandType Application -ErrorAction Stop
$Container = $Settings["KNOWLEDGE_CORE_POSTGRES_CONTAINER"]
& $Docker.Source inspect $Container *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Configured KC PostgreSQL container does not exist: $Container"
}
$Running = (& $Docker.Source inspect --format "{{.State.Running}}" $Container).Trim()
if ($Running -ne "true") {
    & $Docker.Source start $Container *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not start KC PostgreSQL container: $Container"
    }
}

Push-Location -LiteralPath $KCDir
try {
    Write-Host "Current migration state before C07 upgrade:"
    & $Python -m alembic current
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read current Knowledge Core migration state."
    }

    Write-Host "Applying tested Knowledge Core migrations..."
    & $Python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Knowledge Core migration failed."
    }

    Write-Host "Migration state after upgrade:"
    & $Python -m alembic current
    if ($LASTEXITCODE -ne 0) {
        throw "Could not verify final Knowledge Core migration state."
    }
}
finally {
    Pop-Location
}
