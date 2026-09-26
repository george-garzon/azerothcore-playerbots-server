param(
    [string]$CoreDir = "azerothcore-wotlk"
)

$Script = Join-Path $PSScriptRoot "bootstrap.ps1"
& $Script -CoreDir $CoreDir
