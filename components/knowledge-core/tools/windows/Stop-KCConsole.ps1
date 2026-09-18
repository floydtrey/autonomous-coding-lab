param(
    [string]$ConfigPath = (Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "KnowledgeCore\console-v1\console.env"),
    [switch]$StopDatabase
)

$ErrorActionPreference = "Stop"

$StateRoot = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "KnowledgeCore\console-v1"
$PidFile = Join-Path $StateRoot "kc-console.pid"
$KCDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ExpectedService = Join-Path $KCDir "tools\kc_bootstrap_service.py"

if (Test-Path -LiteralPath $PidFile -PathType Leaf) {
    $PidValue = (Get-Content -LiteralPath $PidFile -Raw).Trim()
    $Pid = 0
    if ([int]::TryParse($PidValue, [ref]$Pid)) {
        $Process = Get-CimInstance Win32_Process -Filter "ProcessId=$Pid" -ErrorAction SilentlyContinue
        if ($null -ne $Process) {
            if ($Process.CommandLine -notlike "*$ExpectedService*") {
                throw "Recorded PID $Pid does not match this KC console service. No process was stopped."
            }
            Stop-Process -Id $Pid -Force
            Write-Host "Stopped KC console service PID $Pid."
        }
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

if ($StopDatabase) {
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Config is required to stop the database: $ConfigPath"
    }
    $ContainerLine = Get-Content -LiteralPath $ConfigPath | Where-Object { $_ -like "KNOWLEDGE_CORE_POSTGRES_CONTAINER=*" } | Select-Object -First 1
    if (-not $ContainerLine) {
        throw "KNOWLEDGE_CORE_POSTGRES_CONTAINER is missing from config."
    }
    $Container = $ContainerLine.Substring($ContainerLine.IndexOf("=") + 1)
    $Docker = Get-Command docker.exe -CommandType Application -ErrorAction Stop
    & $Docker.Source stop $Container *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not stop configured KC PostgreSQL container: $Container"
    }
    Write-Host "Stopped configured KC PostgreSQL container."
}
