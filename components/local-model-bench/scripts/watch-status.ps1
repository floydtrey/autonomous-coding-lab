param(
    [string]$Run = "",
    [int]$RefreshSeconds = 2,
    [switch]$Once
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

if ($RefreshSeconds -lt 1) {
    throw "RefreshSeconds must be at least 1."
}

if ($Run) {
    $RunPath = if ([System.IO.Path]::IsPathRooted($Run)) { $Run } else { Join-Path $ProjectRoot $Run }
} else {
    $LatestManifest = Get-ChildItem -Path (Join-Path $ProjectRoot "results") -Filter "manifest.json" -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $LatestManifest) {
        throw "No benchmark run was found. Start a run first or pass -Run with its result folder."
    }
    $RunPath = Split-Path -Parent $LatestManifest.FullName
}

$ManifestPath = Join-Path $RunPath "manifest.json"
$CheckpointPath = Join-Path $RunPath "checkpoint.json"
$TerminalStates = @("completed", "completed_with_errors", "interrupted", "failed")

while (-not (Test-Path -LiteralPath $ManifestPath)) {
    Write-Progress -Activity "Local Model Bench" -Status "Waiting for the run to initialize..." -PercentComplete 0
    if ($Once) { throw "The run has not initialized yet: $RunPath" }
    Start-Sleep -Seconds $RefreshSeconds
}

do {
    $Manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
    $Checkpoint = if (Test-Path -LiteralPath $CheckpointPath) {
        Get-Content -Raw -LiteralPath $CheckpointPath | ConvertFrom-Json
    } else {
        $null
    }

    $Completed = if ($Checkpoint) { [int]$Checkpoint.progress.completed } else { 0 }
    $Total = if ($Checkpoint) { [int]$Checkpoint.progress.total } else { 0 }
    $Percent = if ($Checkpoint) { [double]$Checkpoint.progress.percent } else { 0 }
    $CurrentText = "initializing"
    if ($Checkpoint -and $Checkpoint.current) {
        $CurrentText = "$($Checkpoint.current.model_id) - $($Checkpoint.current.suite_id)/$($Checkpoint.current.case_id)"
    } elseif ($TerminalStates -contains $Manifest.status) {
        $CurrentText = [string]$Manifest.status
    }
    $StatusText = "$Completed of $Total complete - $CurrentText"
    Write-Progress -Activity "Local Model Bench" -Status $StatusText -PercentComplete ([Math]::Min(100, [Math]::Max(0, $Percent)))

    if ($TerminalStates -contains $Manifest.status -or $Once) { break }
    Start-Sleep -Seconds $RefreshSeconds
} while ($true)

Write-Progress -Activity "Local Model Bench" -Completed
Write-Host "Status: $($Manifest.status)"
Write-Host "Progress: $Completed of $Total cases"
Write-Host "Results: $RunPath"
