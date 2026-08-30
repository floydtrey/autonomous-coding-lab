param(
    [switch]$SkipDoctor
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Config = Join-Path $ProjectRoot "configs\planning-round-2.json"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Run scripts\bootstrap.ps1 first."
}

Write-Host "Validating the 90-call planning benchmark..."
& $Python -m localbench validate --config $Config
if ($LASTEXITCODE -ne 0) {
    throw "Planning benchmark validation failed."
}

if (-not $SkipDoctor) {
    Write-Host "Checking Vera, Ollama, and all five configured models..."
    & $Python -m localbench doctor --config $Config
    if ($LASTEXITCODE -ne 0) {
        throw "A provider or model is not ready. Confirm that Ollama is running and Phi-4 finished downloading."
    }
}

& (Join-Path $PSScriptRoot "run-unattended.ps1") -Config $Config
