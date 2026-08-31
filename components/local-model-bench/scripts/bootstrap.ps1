$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    python -m venv (Join-Path $ProjectRoot ".venv")
}

$SitePackages = (& $VenvPython -c "import site; print(site.getsitepackages()[0])").Trim()
$SourcePath = Join-Path $ProjectRoot "src"
Set-Content -Encoding UTF8 -LiteralPath (Join-Path $SitePackages "local_model_bench.pth") -Value $SourcePath
& $VenvPython -m localbench validate --config (Join-Path $ProjectRoot "configs\ollama-16gb.json")
