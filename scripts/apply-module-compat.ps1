param(
    [string]$CoreDir = "azerothcore-wotlk"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$CorePath = Join-Path $RepoRoot $CoreDir
$OllamaPath = Join-Path $CorePath "modules/mod-ollama-chat"
$OllamaPatch = Join-Path $PSScriptRoot "patches/ollama-chat-channels.patch"
if (Test-Path -LiteralPath $OllamaPath) {
    # A failed reverse check means the patch has not been applied yet.
    $SavedErrorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        git -C $OllamaPath apply --reverse --check $OllamaPatch 2>$null
    } finally {
        $ErrorActionPreference = $SavedErrorPreference
    }
    if ($LASTEXITCODE -ne 0) {
        git -C $OllamaPath apply --check $OllamaPatch
        if ($LASTEXITCODE -ne 0) { throw "Ollama channel patch needs review against the updated module." }
        git -C $OllamaPath apply $OllamaPatch
        if ($LASTEXITCODE -ne 0) { throw "Failed to apply Ollama channel patch." }
        Write-Host "Applied Ollama World and battleground chat routing."
    }
}
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
