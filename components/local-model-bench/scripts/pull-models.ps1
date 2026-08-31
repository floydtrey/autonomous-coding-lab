param(
    [string]$Config = "configs\ollama-16gb.json"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigPath = if ([System.IO.Path]::IsPathRooted($Config)) { $Config } else { Join-Path $ProjectRoot $Config }

$OllamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
$OllamaExe = if ($OllamaCommand) {
    $OllamaCommand.Source
} else {
    Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
}
if (-not (Test-Path -LiteralPath $OllamaExe)) {
    throw "Ollama was not found. Install it from https://ollama.com/download/windows and reopen PowerShell."
}

$Settings = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
foreach ($Model in $Settings.models) {
    $Provider = $Settings.providers.($Model.provider)
    if ($Provider.type -eq "ollama") {
        Write-Host "Pulling $($Model.name)..."
        & $OllamaExe pull $Model.name
        if ($LASTEXITCODE -ne 0) { throw "ollama pull failed for $($Model.name)" }
    }
}
