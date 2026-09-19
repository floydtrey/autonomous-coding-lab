param(
    [string]$ServerExe = $env:ACL_LLAMA_SERVER_EXE,
    [string]$HfModel,
    [string]$ModelPath,
    [Parameter(Mandatory = $true)]
    [string]$Alias,
    [int]$Port = 0,
    [string]$HostAddress = "127.0.0.1",
    [int]$GpuLayers = 99,
    [int]$ContextWindow = 32768,
    [int]$Parallel = 1,
    [string]$FlashAttention = "on",
    [string]$Reasoning = "off",
    [double]$Temperature = 0.1,
    [string]$ApiKeyFile = $env:ACL_OPENAI_COMPAT_API_KEY_FILE,
    [string]$LogFile
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ServerExe)) {
    throw "ServerExe is required. Set ACL_LLAMA_SERVER_EXE or pass -ServerExe."
}

$ServerExe = [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($ServerExe))
if (-not (Test-Path -LiteralPath $ServerExe -PathType Leaf)) {
    throw "llama-server executable does not exist: $ServerExe"
}

$HasHf = -not [string]::IsNullOrWhiteSpace($HfModel)
$HasPath = -not [string]::IsNullOrWhiteSpace($ModelPath)
if ($HasHf -eq $HasPath) {
    throw "Specify exactly one of -HfModel or -ModelPath."
}

if ($Port -le 0) {
    $BaseUrl = $env:ACL_OPENAI_COMPAT_BASE_URL
    if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
        throw "Port was not supplied and ACL_OPENAI_COMPAT_BASE_URL is not set."
    }
    try {
        $Uri = [Uri]$BaseUrl
        $Port = $Uri.Port
    } catch {
        throw "ACL_OPENAI_COMPAT_BASE_URL is not a valid URI: $BaseUrl"
    }
}
if ($Port -le 0 -or $Port -gt 65535) {
    throw "Invalid port: $Port"
}

$Listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach ($Listener in $Listeners) {
    $ListenerPid = $Listener.OwningProcess
    if (-not $ListenerPid) { continue }

    $Process = Get-Process -Id $ListenerPid -ErrorAction Stop
    if ($Process.ProcessName -ne "llama-server") {
        throw "Port $Port is owned by $($Process.ProcessName) (PID $ListenerPid), not llama-server. Refusing to terminate it."
    }

    $ObservedPath = $Process.Path
    if (-not [string]::IsNullOrWhiteSpace($ObservedPath) -and [System.IO.Path]::GetFullPath($ObservedPath) -ne $ServerExe) {
        throw "Port $Port is owned by a different llama-server executable: $ObservedPath. Refusing to terminate it."
    }

    Stop-Process -Id $ListenerPid -Force
}

$Deadline = [DateTime]::UtcNow.AddSeconds(15)
do {
    $StillListening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $StillListening) { break }
    Start-Sleep -Milliseconds 200
} while ([DateTime]::UtcNow -lt $Deadline)

if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port did not become free after stopping the previous llama-server."
}

$Args = @()
if ($HasHf) {
    $Args += @("-hf", $HfModel)
} else {
    $ResolvedModelPath = [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($ModelPath))
    if (-not (Test-Path -LiteralPath $ResolvedModelPath -PathType Leaf)) {
        throw "ModelPath does not exist: $ResolvedModelPath"
    }
    $Args += @("-m", $ResolvedModelPath)
}

$Args += @(
    "--alias", $Alias,
    "--host", $HostAddress,
    "--port", "$Port",
    "--gpu-layers", "$GpuLayers",
    "--ctx-size", "$ContextWindow",
    "--parallel", "$Parallel",
    "--flash-attn", $FlashAttention,
    "--cont-batching",
    "--reasoning", $Reasoning,
    "--temp", "$Temperature",
    "--no-mmproj"
)

if (-not [string]::IsNullOrWhiteSpace($ApiKeyFile)) {
    $ResolvedApiKeyFile = [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($ApiKeyFile))
    if (-not (Test-Path -LiteralPath $ResolvedApiKeyFile -PathType Leaf)) {
        throw "API key file does not exist: $ResolvedApiKeyFile"
    }
    $Args += @("--api-key-file", $ResolvedApiKeyFile)
}

if (-not [string]::IsNullOrWhiteSpace($LogFile)) {
    $ResolvedLogFile = [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($LogFile))
    $LogDirectory = Split-Path -Parent $ResolvedLogFile
    if (-not [string]::IsNullOrWhiteSpace($LogDirectory)) {
        New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    }
    $Args += @("--log-file", $ResolvedLogFile, "--log-timestamps")
}

$WorkingDirectory = Split-Path -Parent $ServerExe
$Started = Start-Process -FilePath $ServerExe -ArgumentList $Args -WorkingDirectory $WorkingDirectory -PassThru -WindowStyle Hidden

[pscustomobject]@{
    ok = $true
    pid = $Started.Id
    alias = $Alias
    port = $Port
    server = $ServerExe
    source = $(if ($HasHf) { $HfModel } else { $ResolvedModelPath })
} | ConvertTo-Json -Compress
