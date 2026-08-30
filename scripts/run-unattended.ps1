param(
    [string]$Config = "configs\ollama-16gb.json",
    [string]$Resume = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ConfigPath = if ([System.IO.Path]::IsPathRooted($Config)) { $Config } else { Join-Path $ProjectRoot $Config }
$LogDirectory = Join-Path $ProjectRoot "logs"

if (-not (Test-Path $Python)) {
    throw "Run scripts\bootstrap.ps1 first."
}

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$StdoutLog = Join-Path $LogDirectory "$Stamp.stdout.log"
$StderrLog = Join-Path $LogDirectory "$Stamp.stderr.log"
$Arguments = @("-m", "localbench", "run", "--config", $ConfigPath)
if ($Resume) {
    $ResumePath = if ([System.IO.Path]::IsPathRooted($Resume)) { $Resume } else { Join-Path $ProjectRoot $Resume }
    $Arguments += @("--resume", $ResumePath)
    $RunPath = [System.IO.Path]::GetFullPath($ResumePath)
} else {
    $RunId = "background-$(Get-Date -Format 'yyyyMMddTHHmmss')-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
    $Arguments += @("--run-id", $RunId)
    $Settings = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
    $ResultRootSetting = if ($Settings.result_root) { [string]$Settings.result_root } else { "results" }
    $ResultRoot = [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $ConfigPath) $ResultRootSetting))
    $RunPath = Join-Path $ResultRoot $RunId
}

function ConvertTo-QuotedArgument([string]$Value) {
    return '"' + $Value.Replace('"', '\"') + '"'
}
$ArgumentLine = ($Arguments | ForEach-Object { ConvertTo-QuotedArgument $_ }) -join " "
$Process = Start-Process -FilePath $Python -ArgumentList $ArgumentLine -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog -PassThru
$LaunchRecord = [ordered]@{
    process_id = $Process.Id
    started_at = (Get-Date).ToString("o")
    config = $ConfigPath
    resume = $Resume
    run_path = $RunPath
    stdout_log = $StdoutLog
    stderr_log = $StderrLog
}
$LaunchRecord | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $LogDirectory "$Stamp.pid.json")
Write-Host "Benchmark started in the background (process $($Process.Id))."
Write-Host "Logs: $StdoutLog and $StderrLog"
Write-Host "Progress: .\scripts\watch-status.ps1 -Run `"$RunPath`""
