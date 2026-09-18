param(
    [string[]]$ContainerNames = @("kc-api", "kc-apisix"),
    [string]$StatePath = (Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) ("KnowledgeCore\console-v1\gateway-state-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".json"))
)

$ErrorActionPreference = "Stop"
$Docker = Get-Command docker.exe -CommandType Application -ErrorAction Stop
$Records = @()

foreach ($Name in $ContainerNames) {
    & $Docker.Source inspect $Name *> $null
    if ($LASTEXITCODE -ne 0) {
        $Records += [pscustomobject]@{
            name = $Name
            existed = $false
            was_running = $false
            restart_policy = $null
        }
        continue
    }

    $Running = (& $Docker.Source inspect --format "{{.State.Running}}" $Name).Trim()
    $RestartPolicy = (& $Docker.Source inspect --format "{{.HostConfig.RestartPolicy.Name}}" $Name).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect legacy gateway container: $Name"
    }

    $Records += [pscustomobject]@{
        name = $Name
        existed = $true
        was_running = ($Running -eq "true")
        restart_policy = $RestartPolicy
    }

    & $Docker.Source update --restart=no $Name *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not disable restart policy for legacy gateway container: $Name"
    }

    if ($Running -eq "true") {
        & $Docker.Source stop $Name *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not stop legacy gateway container: $Name"
        }
    }
}

$Parent = Split-Path -Parent $StatePath
New-Item -ItemType Directory -Force -Path $Parent | Out-Null
$Records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatePath -Encoding utf8

foreach ($Record in $Records) {
    if (-not $Record.existed) {
        Write-Host "$($Record.name): not present"
        continue
    }
    $RunningNow = (& $Docker.Source inspect --format "{{.State.Running}}" $Record.name).Trim()
    $RestartNow = (& $Docker.Source inspect --format "{{.HostConfig.RestartPolicy.Name}}" $Record.name).Trim()
    if ($RunningNow -eq "true" -or $RestartNow -ne "no") {
        throw "Legacy gateway privacy disable did not settle for $($Record.name)."
    }
    Write-Host "$($Record.name): stopped; restart policy disabled"
}

Write-Host "Previous gateway state recorded at: $StatePath"
