param(
    [string]$ExistingLauncherPath = "C:\AI\start-kc-cowork-stack.bat",
    [string]$ConfigPath = (Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "KnowledgeCore\console-v1\console.env"),
    [string]$ConsoleProjects = "inbox",
    [string]$DefaultProject = "inbox",
    [switch]$CopyOwnerKey
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ExistingLauncherPath -PathType Leaf)) {
    throw "Existing verified KC launcher not found: $ExistingLauncherPath"
}

$Variables = @{}
foreach ($Line in (Get-Content -LiteralPath $ExistingLauncherPath)) {
    if ($Line -match '^\s*set\s+"([^=]+)=(.*)"\s*$') {
        $Variables[$Matches[1]] = $Matches[2]
    }
}

function Expand-BatchValue {
    param(
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][hashtable]$Known
    )

    $Expanded = $Value
    for ($Pass = 0; $Pass -lt 20; $Pass++) {
        if ($Expanded -notmatch '%([A-Za-z_][A-Za-z0-9_]*)%') {
            break
        }
        $Name = $Matches[1]
        $Token = "%" + $Name + "%"
        $Replacement = $null
        if ($Known.ContainsKey($Name)) {
            $Replacement = [string]$Known[$Name]
        }
        else {
            $Replacement = [Environment]::GetEnvironmentVariable($Name)
        }
        if ($null -eq $Replacement) {
            throw "Could not resolve batch variable $Token from existing KC launcher."
        }
        $Expanded = $Expanded.Replace($Token, $Replacement)
    }

    if ($Expanded -match '%[A-Za-z_][A-Za-z0-9_]*%') {
        throw "Unresolved batch variable remains in KC launcher value."
    }
    return $Expanded
}

foreach ($Name in @(
    "KNOWLEDGE_CORE_DATABASE_URL",
    "KNOWLEDGE_CORE_ARTIFACT_ROOT",
    "KNOWLEDGE_CORE_BOOTSTRAP_KEY",
    "KNOWLEDGE_CORE_BIND_HOST",
    "KNOWLEDGE_CORE_PORT",
    "KC_CONTAINER"
)) {
    if (-not $Variables.ContainsKey($Name) -or -not $Variables[$Name]) {
        throw "Existing KC launcher does not define required setting: $Name"
    }
}

$DatabaseUrl = Expand-BatchValue -Value $Variables["KNOWLEDGE_CORE_DATABASE_URL"] -Known $Variables
$ArtifactRoot = Expand-BatchValue -Value $Variables["KNOWLEDGE_CORE_ARTIFACT_ROOT"] -Known $Variables
$BootstrapKey = Expand-BatchValue -Value $Variables["KNOWLEDGE_CORE_BOOTSTRAP_KEY"] -Known $Variables
$BindHost = Expand-BatchValue -Value $Variables["KNOWLEDGE_CORE_BIND_HOST"] -Known $Variables
$Port = Expand-BatchValue -Value $Variables["KNOWLEDGE_CORE_PORT"] -Known $Variables
$Container = Expand-BatchValue -Value $Variables["KC_CONTAINER"] -Known $Variables

if ($BindHost -ne "127.0.0.1") {
    throw "Existing launcher is not loopback-bound; C07 will not copy it into the local console config."
}

$ProjectList = @($ConsoleProjects.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($ProjectList.Count -eq 0) {
    throw "ConsoleProjects must contain at least one project key."
}
if ($ProjectList -notcontains $DefaultProject) {
    throw "DefaultProject must be present in ConsoleProjects."
}

$Bytes = New-Object byte[] 32
$Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $Rng.GetBytes($Bytes)
}
finally {
    $Rng.Dispose()
}
$ConsoleKey = [Convert]::ToBase64String($Bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
if ($ConsoleKey -eq $BootstrapKey) {
    throw "Generated console key unexpectedly matched the bootstrap key."
}

$Parent = Split-Path -Parent $ConfigPath
New-Item -ItemType Directory -Force -Path $Parent | Out-Null

$Lines = @(
    "KNOWLEDGE_CORE_DATABASE_URL=$DatabaseUrl",
    "KNOWLEDGE_CORE_ARTIFACT_ROOT=$ArtifactRoot",
    "KNOWLEDGE_CORE_BOOTSTRAP_KEY=$BootstrapKey",
    "KNOWLEDGE_CORE_BIND_HOST=127.0.0.1",
    "KNOWLEDGE_CORE_PORT=$Port",
    "KNOWLEDGE_CORE_CONSOLE_ENABLED=true",
    "KNOWLEDGE_CORE_CONSOLE_KEY=$ConsoleKey",
    ("KNOWLEDGE_CORE_CONSOLE_PROJECTS={0}" -f ($ProjectList -join ",")),
    "KNOWLEDGE_CORE_CONSOLE_DEFAULT_PROJECT=$DefaultProject",
    "KNOWLEDGE_CORE_POSTGRES_CONTAINER=$Container"
)
$Lines | Set-Content -LiteralPath $ConfigPath -Encoding utf8

Write-Host "Created KC console config from the verified existing launcher:"
Write-Host "  $ConfigPath"
Write-Host "Database/artifact/bootstrap values were not printed."

if ($CopyOwnerKey -and (Get-Command Set-Clipboard -ErrorAction SilentlyContinue)) {
    $ConsoleKey | Set-Clipboard
    Write-Host "New console owner key copied to clipboard."
}
else {
    Write-Host "The generated console owner key is stored only in the local config file."
}
