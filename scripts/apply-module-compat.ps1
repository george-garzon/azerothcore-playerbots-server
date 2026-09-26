param(
    [string]$CoreDir = "azerothcore-wotlk"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$CorePath = Join-Path $RepoRoot $CoreDir
$ModulePath = Join-Path $CorePath "modules/DungeonRespawn/src"
$PlayerScriptPath = Join-Path $CorePath "src/server/game/Scripting/ScriptDefines/PlayerScript.h"

if ((Test-Path -LiteralPath $ModulePath) -and (Test-Path -LiteralPath $PlayerScriptPath)) {
    $playerScript = [System.IO.File]::ReadAllText($PlayerScriptPath)
    $hooks = @{
        OnBeforeTeleport = "OnPlayerBeforeTeleport"
        OnMapChanged = "OnPlayerMapChanged"
        OnLogin = "OnPlayerLogin"
        OnLogout = "OnPlayerLogout"
    }

    foreach ($name in @("DungeonRespawn.h", "DungeonRespawn.cpp")) {
        $path = Join-Path $ModulePath $name
        $original = [System.IO.File]::ReadAllText($path)
        $updated = $original
        foreach ($oldName in $hooks.Keys) {
            $newName = $hooks[$oldName]
            if ($playerScript -match "\b$newName\s*\(") {
                $updated = $updated -replace "\b$oldName\s*(?=\()", $newName
            }
        }
        if ($updated -ne $original) {
            [System.IO.File]::WriteAllText($path, $updated, (New-Object System.Text.UTF8Encoding($false)))
            Write-Host "Updated DungeonRespawn player hooks in $name"
        }
    }
}
