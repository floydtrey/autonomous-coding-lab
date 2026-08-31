param(
    [Parameter(Mandatory = $true)]
    [string]$TaskId,
    [string]$Packet = "real-tasks-v1",
    [string]$DestinationRoot = "",
    [string]$SourceRepository = "",
    [string]$UpstreamOutput = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))

function Get-FullPath([string]$Path, [string]$Base) {
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $Base $Path))
}

function Assert-SafeId([string]$Value, [string]$Label) {
    if ($Value -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$') {
        throw "$Label is not a safe identifier: $Value"
    }
}

function Assert-PathWithin([string]$Child, [string]$Parent, [string]$Label) {
    $ParentPrefix = $Parent.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $Child.StartsWith($ParentPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label escapes its allowed directory: $Child"
    }
}

$PacketDirectory = if ([System.IO.Path]::IsPathRooted($Packet)) {
    [System.IO.Path]::GetFullPath($Packet)
} else {
    [System.IO.Path]::GetFullPath((Join-Path (Join-Path $ProjectRoot "validation-packets") $Packet))
}
$PacketPath = Join-Path $PacketDirectory "packet.json"
if (-not (Test-Path -LiteralPath $PacketPath -PathType Leaf)) {
    throw "Validation packet not found: $PacketPath"
}

$Manifest = Get-Content -Raw -LiteralPath $PacketPath | ConvertFrom-Json
Assert-SafeId ([string]$Manifest.packet_id) "packet id"
Assert-SafeId $TaskId "task id"
$Matches = @($Manifest.tasks | Where-Object { $_.id -eq $TaskId })
if ($Matches.Count -ne 1) {
    throw "Task id must match exactly one packet task: $TaskId"
}
$Task = $Matches[0]
$Commit = [string]$Task.source.baseline_commit
if ($Commit -notmatch '^[0-9a-fA-F]{7,40}$') {
    throw "Task baseline must be an exact hexadecimal commit: $Commit"
}
if ($Task.source.materialization -ne "git archive") {
    throw "Unsupported task materialization: $($Task.source.materialization)"
}

$SourcePath = if ($SourceRepository) {
    Get-FullPath $SourceRepository $ProjectRoot
} else {
    $ProjectRoot
}
if (-not (Test-Path -LiteralPath (Join-Path $SourcePath ".git"))) {
    throw "Source repository has no .git directory: $SourcePath"
}
$ResolvedCommit = (& git -C $SourcePath rev-parse --verify "$Commit^{commit}").Trim()
if ($LASTEXITCODE -ne 0 -or $ResolvedCommit -notmatch '^[0-9a-fA-F]{40}$') {
    throw "Baseline commit is not available in the source repository: $Commit"
}

$DestinationPath = if ($DestinationRoot) {
    Get-FullPath $DestinationRoot $ProjectRoot
} else {
    Join-Path ([System.IO.Path]::GetTempPath()) "local-model-bench-validation"
}
New-Item -ItemType Directory -Force -Path $DestinationPath | Out-Null
$Stamp = Get-Date -Format "yyyyMMddTHHmmss"
$Suffix = [guid]::NewGuid().ToString("N").Substring(0, 8)
$WorkspaceName = "$($Manifest.packet_id)-$TaskId-$Stamp-$Suffix"
$WorkspacePath = [System.IO.Path]::GetFullPath((Join-Path $DestinationPath $WorkspaceName))
Assert-PathWithin $WorkspacePath ([System.IO.Path]::GetFullPath($DestinationPath)) "workspace"
New-Item -ItemType Directory -Path $WorkspacePath | Out-Null
$RepositoryPath = Join-Path $WorkspacePath "repository"
New-Item -ItemType Directory -Path $RepositoryPath | Out-Null
$ArchivePath = Join-Path $WorkspacePath "baseline.zip"

& git -C $SourcePath archive --format=zip "--output=$ArchivePath" $ResolvedCommit
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $ArchivePath)) {
    throw "git archive failed for baseline $ResolvedCommit; incomplete workspace retained at $WorkspacePath"
}
Expand-Archive -LiteralPath $ArchivePath -DestinationPath $RepositoryPath
Remove-Item -LiteralPath $ArchivePath -Force

& git -c core.longpaths=true -C $RepositoryPath init -b baseline | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not initialize the candidate repository" }
& git -C $RepositoryPath config user.name "Local Model Bench"
& git -C $RepositoryPath config user.email "local-model-bench@invalid.local"
& git -C $RepositoryPath config core.autocrlf false
& git -c core.longpaths=true -C $RepositoryPath add -A
& git -c core.longpaths=true -c commit.gpgSign=false -C $RepositoryPath commit -m "Validation baseline $ResolvedCommit" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not commit the candidate baseline" }
$CandidateHead = (& git -C $RepositoryPath rev-parse HEAD).Trim()

$ScopePath = Get-FullPath ([string]$Task.candidate_scope) $PacketDirectory
Assert-PathWithin $ScopePath $PacketDirectory "candidate scope"
if (-not (Test-Path -LiteralPath $ScopePath -PathType Leaf)) {
    throw "Candidate scope file not found: $ScopePath"
}
Copy-Item -LiteralPath $ScopePath -Destination (Join-Path $WorkspacePath "TASK.md")
$CandidateFiles = @("TASK.md")

if ($Task.candidate_evidence) {
    $EvidencePath = Get-FullPath ([string]$Task.candidate_evidence) $PacketDirectory
    Assert-PathWithin $EvidencePath $PacketDirectory "candidate evidence"
    if (-not (Test-Path -LiteralPath $EvidencePath -PathType Leaf)) {
        throw "Candidate evidence file not found: $EvidencePath"
    }
    Copy-Item -LiteralPath $EvidencePath -Destination (Join-Path $WorkspacePath "EVIDENCE.md")
    $CandidateFiles += "EVIDENCE.md"
}

if ($UpstreamOutput) {
    $UpstreamPath = Get-FullPath $UpstreamOutput (Get-Location).Path
    if (-not (Test-Path -LiteralPath $UpstreamPath -PathType Leaf)) {
        throw "Upstream stage output not found: $UpstreamPath"
    }
    Copy-Item -LiteralPath $UpstreamPath -Destination (Join-Path $WorkspacePath "UPSTREAM.md")
    $CandidateFiles += "UPSTREAM.md"
}

$CandidateHashes = [ordered]@{}
foreach ($Name in $CandidateFiles) {
    $CandidateHashes[$Name] = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $WorkspacePath $Name)).Hash.ToLowerInvariant()
}
$Record = [ordered]@{
    schema_version = 1
    packet_id = [string]$Manifest.packet_id
    task_id = [string]$Task.id
    title = [string]$Task.title
    category = [string]$Task.category
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    source_repository = [string]$Task.source.repository
    source_commit = $ResolvedCommit
    candidate_repository_head = $CandidateHead
    repository_directory = "repository"
    candidate_files = $CandidateHashes
    assessment_included = $false
    network_policy = [string]$Task.limits.network
    wall_seconds = [int]$Task.limits.wall_seconds
    max_attempts = [int]$Task.limits.max_attempts
}
$Record | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $WorkspacePath "validation-workspace.json")

Write-Host "Validation workspace ready: $WorkspacePath"
Write-Host "Task: $TaskId - $($Task.title)"
Write-Host "Repository: $RepositoryPath"
Write-Host "Candidate instructions: $(Join-Path $WorkspacePath 'TASK.md')"
Write-Host "Assessment files were not included."
