param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [string]$Python = "",
    [string]$OutputRoot = "artifacts\release",
    [switch]$SkipSmokeTest
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-ManifestVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $match = Select-String -Path $Path -Pattern '^version\s*=\s*"([^"]+)"\s*$' | Select-Object -First 1
    if ($null -eq $match) {
        throw "Could not read a version from $Path."
    }

    return $match.Matches[0].Groups[1].Value
}

function Get-ChangelogSection {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Version
    )

    $lines = Get-Content $Path
    $startIndex = -1
    for ($index = 0; $index -lt $lines.Length; $index++) {
        if ($lines[$index] -match ("^## \[" + [regex]::Escape($Version) + "\]")) {
            $startIndex = $index
            break
        }
    }

    if ($startIndex -lt 0) {
        throw "CHANGELOG.md does not contain a section for version $Version."
    }

    $endIndex = $lines.Length
    for ($index = $startIndex + 1; $index -lt $lines.Length; $index++) {
        if ($lines[$index] -match '^## \[') {
            $endIndex = $index
            break
        }
    }

    return ($lines[$startIndex..($endIndex - 1)] -join [Environment]::NewLine).Trim()
}

$normalizedVersion = $Version.Trim()
if ($normalizedVersion.StartsWith("v")) {
    $normalizedVersion = $normalizedVersion.Substring(1)
}

if ($normalizedVersion -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version must be in semantic version form, for example 0.2.0."
}

$releaseTag = "v$normalizedVersion"
$repoRoot = Split-Path -Parent $PSScriptRoot
$orchestratorRoot = Join-Path $repoRoot "python\orchestrator"
$buildScript = Join-Path $orchestratorRoot "build_windows.ps1"
$docsRoot = Join-Path $repoRoot "docs"
$samplesRoot = Join-Path $orchestratorRoot "samples"
$outputRootPath = Join-Path $repoRoot $OutputRoot
$releaseDirName = "PathFlowGuard-$releaseTag-windows-x64"
$releaseDir = Join-Path $outputRootPath $releaseDirName
$releaseNotesPath = Join-Path $outputRootPath "RELEASE_NOTES.md"
$exeAssetPath = Join-Path $outputRootPath "$releaseDirName.exe"
$zipAssetPath = Join-Path $outputRootPath "$releaseDirName.zip"
$checksumsPath = Join-Path $outputRootPath "SHA256SUMS.txt"

Set-Location $repoRoot

$pythonVersion = Get-ManifestVersion -Path (Join-Path $orchestratorRoot "pyproject.toml")
$rustVersion = Get-ManifestVersion -Path (Join-Path $repoRoot "rust\attestor\Cargo.toml")
if ($pythonVersion -ne $normalizedVersion) {
    throw "python/orchestrator/pyproject.toml has version $pythonVersion, expected $normalizedVersion."
}
if ($rustVersion -ne $normalizedVersion) {
    throw "rust/attestor/Cargo.toml has version $rustVersion, expected $normalizedVersion."
}

$releaseNotesSection = Get-ChangelogSection -Path (Join-Path $repoRoot "CHANGELOG.md") -Version $normalizedVersion

if ($Python -and -not $SkipSmokeTest) {
    & $buildScript -Python $Python -SmokeTest
}
elseif ($Python) {
    & $buildScript -Python $Python
}
elseif (-not $SkipSmokeTest) {
    & $buildScript -SmokeTest
}
else {
    & $buildScript
}

New-Item -ItemType Directory -Path $outputRootPath -Force | Out-Null
if (Test-Path -LiteralPath $releaseDir) {
    Remove-Item -LiteralPath $releaseDir -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $orchestratorRoot "dist\PathFlowGuard.exe") -Destination (Join-Path $releaseDir "PathFlowGuard.exe") -Force
Copy-Item -LiteralPath (Join-Path $repoRoot "README.md") -Destination $releaseDir -Force
Copy-Item -LiteralPath (Join-Path $repoRoot "CHANGELOG.md") -Destination $releaseDir -Force
Copy-Item -LiteralPath (Join-Path $repoRoot "SECURITY.md") -Destination $releaseDir -Force
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination $releaseDir -Force
Copy-Item -LiteralPath $docsRoot -Destination (Join-Path $releaseDir "docs") -Recurse -Force
Copy-Item -LiteralPath $samplesRoot -Destination (Join-Path $releaseDir "samples") -Recurse -Force

$releaseNotes = @(
    "# PathFlow Guard $releaseTag",
    "",
    $releaseNotesSection
) -join [Environment]::NewLine
Set-Content -LiteralPath $releaseNotesPath -Value $releaseNotes
Copy-Item -LiteralPath $releaseNotesPath -Destination (Join-Path $releaseDir "RELEASE_NOTES.md") -Force

Copy-Item -LiteralPath (Join-Path $releaseDir "PathFlowGuard.exe") -Destination $exeAssetPath -Force
if (Test-Path -LiteralPath $zipAssetPath) {
    Remove-Item -LiteralPath $zipAssetPath -Force
}
Compress-Archive -Path $releaseDir -DestinationPath $zipAssetPath -Force

$exeHash = Get-FileHash -LiteralPath $exeAssetPath -Algorithm SHA256
$zipHash = Get-FileHash -LiteralPath $zipAssetPath -Algorithm SHA256
@(
    "$($exeHash.Hash.ToLower())  $([System.IO.Path]::GetFileName($exeAssetPath))"
    "$($zipHash.Hash.ToLower())  $([System.IO.Path]::GetFileName($zipAssetPath))"
) | Set-Content -LiteralPath $checksumsPath

Write-Host ""
Write-Host "Release assets created:"
Write-Host "  $exeAssetPath"
Write-Host "  $zipAssetPath"
Write-Host "  $checksumsPath"
Write-Host "  $releaseNotesPath"
