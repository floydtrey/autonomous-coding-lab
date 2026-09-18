param(
    [string]$ConfigPath = (Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "KnowledgeCore\console-v1\console.env"),
    [switch]$NoBrowser,
    [switch]$CopyOwnerKey
)

$ErrorActionPreference = "Stop"

function Import-KCConsoleConfig {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "KC console config not found: $Path"
    }

    $Allowed = @(
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
    )
    $Result = @{}

    foreach ($RawLine in (Get-Content -LiteralPath $Path)) {
        $Line = $RawLine.Trim()
        if (-not $Line -or $Line.StartsWith("#")) {
            continue
        }
        $Equals = $Line.IndexOf("=")
        if ($Equals -lt 1) {
            throw "Invalid KC console config line. Expected NAME=value."
        }
        $Name = $Line.Substring(0, $Equals).Trim()
        $Value = $Line.Substring($Equals + 1)
        if ($Allowed -notcontains $Name) {
            throw "Unknown KC console config key: $Name"
        }
        $Result[$Name] = $Value
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
        if (-not $Result.ContainsKey($Required) -or -not $Result[$Required]) {
            throw "Required KC console config key is missing: $Required"
        }
    }

    return $Result
}

$Settings = Import-KCConsoleConfig -Path $ConfigPath

if ($Settings["KNOWLEDGE_CORE_BIND_HOST"] -ne "127.0.0.1") {
    throw "KC Console V1 daily launcher requires KNOWLEDGE_CORE_BIND_HOST=127.0.0.1."
}
if ($Settings["KNOWLEDGE_CORE_CONSOLE_ENABLED"].ToLowerInvariant() -notin @("1", "true", "yes", "on")) {
    throw "KC console is not enabled in the selected config."
}
if ($Settings["KNOWLEDGE_CORE_CONSOLE_KEY"] -eq $Settings["KNOWLEDGE_CORE_BOOTSTRAP_KEY"]) {
    throw "KC console owner key must differ from the bootstrap key."
}

foreach ($Name in $Settings.Keys) {
    if ($Name -eq "KNOWLEDGE_CORE_POSTGRES_CONTAINER") {
        continue
    }
    Set-Item -Path "Env:$Name" -Value $Settings[$Name]
}

$KCDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Service = Join-Path $KCDir "tools\kc_bootstrap_service.py"
$Python = Join-Path $KCDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    $PythonCommand = Get-Command python.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $Python = $PythonCommand.Source
}
if (-not (Test-Path -LiteralPath $Service -PathType Leaf)) {
    throw "KC bootstrap service not found: $Service"
}

$Port = 0
if (-not [int]::TryParse($Settings["KNOWLEDGE_CORE_PORT"], [ref]$Port) -or $Port -lt 1 -or $Port -gt 65535) {
    throw "KNOWLEDGE_CORE_PORT must be a valid TCP port."
}
$BaseUrl = "http://127.0.0.1:$Port"
$ConsoleUrl = "$BaseUrl/console/"

function Test-KCConsoleHttp {
    try {
        $Response = Invoke-WebRequest -Uri $ConsoleUrl -UseBasicParsing -TimeoutSec 3
        return $Response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

$Listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($Listeners.Count -gt 0) {
    if (-not (Test-KCConsoleHttp)) {
        $Owners = ($Listeners.OwningProcess | Sort-Object -Unique) -join ", "
        throw "Port $Port is already owned by PID(s) $Owners, but the KC console did not answer. No process was killed."
    }

    if ($CopyOwnerKey -and (Get-Command Set-Clipboard -ErrorAction SilentlyContinue)) {
        $Settings["KNOWLEDGE_CORE_CONSOLE_KEY"] | Set-Clipboard
        Write-Host "KC console is already running. Owner key copied to clipboard."
    }
    else {
        Write-Host "KC console is already running."
    }

    if (-not $NoBrowser) {
        Start-Process $ConsoleUrl
    }
    exit 0
}

$Docker = Get-Command docker.exe -CommandType Application -ErrorAction Stop
$Container = $Settings["KNOWLEDGE_CORE_POSTGRES_CONTAINER"]

& $Docker.Source inspect $Container *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Configured KC PostgreSQL container does not exist: $Container"
}
$Running = (& $Docker.Source inspect --format "{{.State.Running}}" $Container).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not inspect KC PostgreSQL container: $Container"
}
if ($Running -ne "true") {
    Write-Host "Starting configured KC PostgreSQL container..."
    & $Docker.Source start $Container *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not start KC PostgreSQL container: $Container"
    }
}

$StateRoot = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "KnowledgeCore\console-v1"
$LogRoot = Join-Path $StateRoot "logs"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$StdoutLog = Join-Path $LogRoot "kc-console-$Timestamp.out.log"
$StderrLog = Join-Path $LogRoot "kc-console-$Timestamp.err.log"
$PidFile = Join-Path $StateRoot "kc-console.pid"

$ServiceArgument = [char]34 + $Service + [char]34
$Process = Start-Process -FilePath $Python -ArgumentList @("-B", $ServiceArgument) -WorkingDirectory $KCDir -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog -PassThru -WindowStyle Hidden

$Process.Id | Set-Content -LiteralPath $PidFile -Encoding ascii

$Deadline = (Get-Date).AddSeconds(45)
do {
    $Process.Refresh()
    if ($Process.HasExited) {
        $ErrorText = if (Test-Path -LiteralPath $StderrLog) {
            (Get-Content -LiteralPath $StderrLog -Tail 30) -join [Environment]::NewLine
        }
        else {
            "No stderr log was produced."
        }
        throw "KC console service exited before becoming ready. Log: $StderrLog" + [Environment]::NewLine + $ErrorText
    }

    if (Test-KCConsoleHttp) {
        if ($CopyOwnerKey -and (Get-Command Set-Clipboard -ErrorAction SilentlyContinue)) {
            $Settings["KNOWLEDGE_CORE_CONSOLE_KEY"] | Set-Clipboard
            Write-Host "KC console ready. Owner key copied to clipboard."
        }
        else {
            Write-Host "KC console ready."
        }
        Write-Host "URL: $ConsoleUrl"
        Write-Host "Models, Cowork, and Graphiti were not started."
        if (-not $NoBrowser) {
            Start-Process $ConsoleUrl
        }
        exit 0
    }

    Start-Sleep -Seconds 1
} while ((Get-Date) -lt $Deadline)

throw "KC console did not become ready on port $Port. Logs: $StdoutLog ; $StderrLog"
