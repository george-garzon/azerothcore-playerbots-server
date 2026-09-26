param(
    [string]$CoreDir = "azerothcore-wotlk"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$CorePath = Join-Path $RepoRoot $CoreDir
$ModulesPath = Join-Path $CorePath "modules"

function Sync-GitRepository {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Branch
    )

    if (Test-Path -LiteralPath $Path) {
        if (-not (Test-Path -LiteralPath (Join-Path $Path ".git"))) {
            throw "Refusing to use '$Path' because it exists but is not a git repository."
        }

        git -C $Path fetch origin $Branch
        git -C $Path checkout $Branch
        git -C $Path pull --ff-only origin $Branch
        return
    }

    git clone --branch $Branch --depth 1 $Url $Path
}

Set-Location $RepoRoot

Sync-GitRepository `
    -Path $CorePath `
    -Url "https://github.com/mod-playerbots/azerothcore-wotlk.git" `
    -Branch "Playerbot"

New-Item -ItemType Directory -Path $ModulesPath -Force | Out-Null

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-playerbots") `
    -Url "https://github.com/mod-playerbots/mod-playerbots.git" `
    -Branch "master"

$LegacyAhBotPath = Join-Path $ModulesPath "mod-ah-bot"
if (Test-Path -LiteralPath $LegacyAhBotPath) {
    Remove-Item -LiteralPath $LegacyAhBotPath -Recurse -Force
    Write-Host "Removed legacy mod-ah-bot; this stack uses mod-ah-bot-plus."
}

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-dungeon-clear") `
    -Url "https://github.com/jrad7/mod-dungeon-clear.git" `
    -Branch "master"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-autobalance") `
    -Url "https://github.com/azerothcore/mod-autobalance.git" `
    -Branch "master"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-ah-bot-plus") `
    -Url "https://github.com/NathanHandley/mod-ah-bot-plus.git" `
    -Branch "master"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-individual-progression") `
    -Url "https://github.com/ZhengPeiRu21/mod-individual-progression.git" `
    -Branch "master"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-transmog") `
    -Url "https://github.com/azerothcore/mod-transmog.git" `
    -Branch "master"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-aoe-loot") `
    -Url "https://github.com/azerothcore/mod-aoe-loot.git" `
    -Branch "master"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "DungeonRespawn") `
    -Url "https://github.com/AnchyDev/DungeonRespawn.git" `
    -Branch "master"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-npc-all-mounts") `
    -Url "https://github.com/azerothcore/mod-npc-all-mounts.git" `
    -Branch "master"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-money-for-kills") `
    -Url "https://github.com/azerothcore/mod-money-for-kills.git" `
    -Branch "master"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-multibot-bridge") `
    -Url "https://github.com/Wishmaster117/mod-multibot-bridge.git" `
    -Branch "main"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "portals-in-all-capitals") `
    -Url "https://github.com/azerothcore/portals-in-all-capitals.git" `
    -Branch "main"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-ollama-chat") `
    -Url "https://github.com/DustinHendrickson/mod-ollama-chat.git" `
    -Branch "main"

Sync-GitRepository `
    -Path (Join-Path $ModulesPath "mod-ale") `
    -Url "https://github.com/azerothcore/mod-ale.git" `
    -Branch "master"

$EnvPath = Join-Path $RepoRoot ".env"
$EnvExamplePath = Join-Path $RepoRoot ".env.example"
if (-not (Test-Path -LiteralPath $EnvPath)) {
    Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
    Write-Host "Created .env from .env.example. Change DOCKER_DB_ROOT_PASSWORD before exposing this server."
} else {
    $existingKeys = @{}
    foreach ($line in Get-Content -LiteralPath $EnvPath) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }

        $existingKeys[$trimmed.Split("=", 2)[0].Trim()] = $true
    }

    $missingLines = @()
    foreach ($line in Get-Content -LiteralPath $EnvExamplePath) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }

        $key = $trimmed.Split("=", 2)[0].Trim()
        if (-not $existingKeys.ContainsKey($key)) {
            $missingLines += $line
        }
    }

    if ($missingLines.Count -gt 0) {
        Add-Content -LiteralPath $EnvPath -Value ""
        Add-Content -LiteralPath $EnvPath -Value "# Added from .env.example by bootstrap.ps1"
        Add-Content -LiteralPath $EnvPath -Value $missingLines
        Write-Host "Appended $($missingLines.Count) missing .env setting(s) from .env.example."
    }
}

& (Join-Path $PSScriptRoot "apply-config.ps1") -CoreDir $CoreDir

Write-Host "AzerothCore Playerbot fork and modules are ready in $CorePath"
Write-Host "Run: docker compose up -d --build"
