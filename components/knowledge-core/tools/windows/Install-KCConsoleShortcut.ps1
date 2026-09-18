param(
    [string]$ConfigPath = (Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "KnowledgeCore\console-v1\console.env"),
    [string]$ShortcutPath = (Join-Path ([Environment]::GetFolderPath("Desktop")) "Knowledge Core.lnk"),
    [bool]$CopyOwnerKey = $true
)

$ErrorActionPreference = "Stop"

$StartScript = Join-Path $PSScriptRoot "Start-KCConsole.ps1"
if (-not (Test-Path -LiteralPath $StartScript -PathType Leaf)) {
    throw "KC console start script not found: $StartScript"
}
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "KC console config not found: $ConfigPath"
}

$PowerShell = (Get-Command powershell.exe -CommandType Application -ErrorAction Stop).Source
$Quote = [char]34
$Arguments = "-NoProfile -ExecutionPolicy Bypass -File " + $Quote + $StartScript + $Quote + " -ConfigPath " + $Quote + $ConfigPath + $Quote
if ($CopyOwnerKey) {
    $Arguments += " -CopyOwnerKey"
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PowerShell
$Shortcut.Arguments = $Arguments
$Shortcut.WorkingDirectory = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Shortcut.Description = "Start the local Knowledge Core notebook only"
$Shortcut.Save()

Write-Host "Created shortcut: $ShortcutPath"
