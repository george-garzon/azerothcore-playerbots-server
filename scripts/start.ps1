param(
    [string]$CoreDir = "azerothcore-wotlk"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$CorePath = Join-Path $RepoRoot $CoreDir

if (-not (Test-Path -LiteralPath (Join-Path $CorePath ".git"))) {
    & (Join-Path $PSScriptRoot "bootstrap.ps1") -CoreDir $CoreDir
}

Set-Location $RepoRoot
& (Join-Path $PSScriptRoot "apply-config.ps1") -CoreDir $CoreDir
docker compose up -d --build
