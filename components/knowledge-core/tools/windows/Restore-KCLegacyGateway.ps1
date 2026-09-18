param(
    [Parameter(Mandatory = $true)][string]$StatePath
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
    throw "Gateway state file not found: $StatePath"
}

$Docker = Get-Command docker.exe -CommandType Application -ErrorAction Stop
$Records = @(Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json)

foreach ($Record in $Records) {
    if (-not $Record.existed) {
        continue
    }

    & $Docker.Source inspect $Record.name *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Previously present gateway container is now missing: $($Record.name)"
    }

    $Policy = [string]$Record.restart_policy
    if (-not $Policy) {
        $Policy = "no"
    }
    & $Docker.Source update --restart=$Policy $Record.name *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not restore restart policy for $($Record.name)"
    }

    if ($Record.was_running) {
        & $Docker.Source start $Record.name *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not restart $($Record.name)"
        }
    }
}

Write-Host "Legacy gateway state restored from: $StatePath"
