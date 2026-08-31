param(
    [switch]$SkipDoctor
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Config = Join-Path $ProjectRoot "configs\planning-round-2-qwen14-json.json"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Run scripts\bootstrap.ps1 first."
}

Write-Host "Validating the 18-call Qwen 14B native-JSON retest..."
& $Python -m localbench validate --config $Config
if ($LASTEXITCODE -ne 0) {
    throw "Qwen 14B native-JSON retest validation failed."
}

if (-not $SkipDoctor) {
    Write-Host "Checking Ollama and Qwen 14B..."
    & $Python -m localbench doctor --config $Config
    if ($LASTEXITCODE -ne 0) {
        throw "Ollama or Qwen 14B is not ready."
    }
}

& (Join-Path $PSScriptRoot "run-unattended.ps1") -Config $Config
