param(
    [string]$CoreDir = "azerothcore-wotlk"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$CorePath = Join-Path $RepoRoot $CoreDir
$EnvExamplePath = Join-Path $RepoRoot ".env.example"
$EnvPath = Join-Path $RepoRoot ".env"

function Read-DotEnv {
    param([Parameter(Mandatory = $true)][string]$Path)

    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $values
    }

    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#")) {
            continue
        }

        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -ne 2) {
            continue
        }

        $values[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
    }

    return $values
}

$defaults = Read-DotEnv -Path $EnvExamplePath
$overrides = Read-DotEnv -Path $EnvPath

function Get-Setting {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$Fallback = ""
    )

    if ($overrides.ContainsKey($Name)) {
        return $overrides[$Name]
    }

    if ($defaults.ContainsKey($Name)) {
        return $defaults[$Name]
    }

    return $Fallback
}

$ModuleConfigPath = Join-Path $CorePath "env/dist/etc/modules"
New-Item -ItemType Directory -Path $ModuleConfigPath -Force | Out-Null

$playerbotsConfig = @"
[worldserver]
AiPlayerbot.Enabled = 1
AiPlayerbot.RandomBotAutologin = 1
AiPlayerbot.MinRandomBots = $(Get-Setting -Name "BOT_MIN" -Fallback "1500")
AiPlayerbot.MaxRandomBots = $(Get-Setting -Name "BOT_MAX" -Fallback "1500")
AiPlayerbot.RandomBotAccountCount = $(Get-Setting -Name "BOT_ACCOUNT_COUNT" -Fallback "0")
AiPlayerbot.AddClassAccountPoolSize = $(Get-Setting -Name "ADDCLASS_ACCOUNT_POOL_SIZE" -Fallback "50")
AiPlayerbot.RandomBotMinLevel = $(Get-Setting -Name "RANDOM_BOT_MIN_LEVEL" -Fallback "1")
AiPlayerbot.RandomBotMaxLevel = $(Get-Setting -Name "RANDOM_BOT_MAX_LEVEL" -Fallback "80")
AiPlayerbot.MaxAddedBots = $(Get-Setting -Name "MAX_ADDED_BOTS" -Fallback "40")
AiPlayerbot.GroupInvitationPermission = $(Get-Setting -Name "GROUP_INVITATION_PERMISSION" -Fallback "2")
AiPlayerbot.ApplyInstanceStrategies = $(Get-Setting -Name "APPLY_INSTANCE_STRATEGIES" -Fallback "1")
AiPlayerbot.SummonWhenGroup = $(Get-Setting -Name "SUMMON_WHEN_GROUP" -Fallback "1")
AiPlayerbot.AutoAvoidAoe = $(Get-Setting -Name "AUTO_AVOID_AOE" -Fallback "1")
AiPlayerbot.AutoPartyBuffs = $(Get-Setting -Name "AUTO_PARTY_BUFFS" -Fallback "2")
AiPlayerbot.SyncQuestWithPlayer = $(Get-Setting -Name "SYNC_QUEST_WITH_PLAYER" -Fallback "1")
AiPlayerbot.SyncLevelWithPlayers = $(Get-Setting -Name "SYNC_LEVEL_WITH_PLAYERS" -Fallback "1")
AiPlayerbot.RandomBotJoinLfg = $(Get-Setting -Name "RANDOM_BOT_JOIN_LFG" -Fallback "1")
AiPlayerbot.RandomBotJoinBG = $(Get-Setting -Name "RANDOM_BOT_JOIN_BG" -Fallback "1")
AiPlayerbot.RandomBotAutoJoinBG = $(Get-Setting -Name "RANDOM_BOT_AUTO_JOIN_BG" -Fallback "1")
AiPlayerbot.RandomBotAutoJoinWSBrackets = $(Get-Setting -Name "RANDOM_BOT_BG_WS_BRACKETS" -Fallback "7")
AiPlayerbot.RandomBotAutoJoinABBrackets = $(Get-Setting -Name "RANDOM_BOT_BG_AB_BRACKETS" -Fallback "6")
AiPlayerbot.RandomBotAutoJoinAVBrackets = $(Get-Setting -Name "RANDOM_BOT_BG_AV_BRACKETS" -Fallback "3")
AiPlayerbot.RandomBotAutoJoinEYBrackets = $(Get-Setting -Name "RANDOM_BOT_BG_EY_BRACKETS" -Fallback "2")
AiPlayerbot.RandomBotAutoJoinICBrackets = $(Get-Setting -Name "RANDOM_BOT_BG_IC_BRACKETS" -Fallback "1")
AiPlayerbot.RandomBotAutoJoinBGWSCount = $(Get-Setting -Name "RANDOM_BOT_BG_WS_COUNT" -Fallback "1")
AiPlayerbot.RandomBotAutoJoinBGABCount = $(Get-Setting -Name "RANDOM_BOT_BG_AB_COUNT" -Fallback "1")
AiPlayerbot.RandomBotAutoJoinBGAVCount = $(Get-Setting -Name "RANDOM_BOT_BG_AV_COUNT" -Fallback "0")
AiPlayerbot.RandomBotAutoJoinBGEYCount = $(Get-Setting -Name "RANDOM_BOT_BG_EY_COUNT" -Fallback "1")
AiPlayerbot.RandomBotAutoJoinBGICCount = $(Get-Setting -Name "RANDOM_BOT_BG_IC_COUNT" -Fallback "0")
"@

$ahbotConfig = @"
[worldserver]
AuctionHouseBot.EnableSeller = $(if ((Get-Setting -Name "AHBOT_ENABLE_SELLER" -Fallback "1") -eq "1") { "true" } else { "false" })
AuctionHouseBot.Buyer.Enabled = $(if ((Get-Setting -Name "AHBOT_ENABLE_BUYER" -Fallback "1") -eq "1") { "true" } else { "false" })
AuctionHouseBot.GUIDs = $(Get-Setting -Name "AHBOT_GUIDS" -Fallback "0")
AuctionHouseBot.ItemsPerCycle = $(Get-Setting -Name "AHBOT_ITEMS_PER_CYCLE" -Fallback "400")
AuctionHouseBot.Alliance.MinItems = $(Get-Setting -Name "AHBOT_ALLIANCE_MIN_ITEMS" -Fallback "25000")
AuctionHouseBot.Alliance.MaxItems = $(Get-Setting -Name "AHBOT_ALLIANCE_MAX_ITEMS" -Fallback "25000")
AuctionHouseBot.Horde.MinItems = $(Get-Setting -Name "AHBOT_HORDE_MIN_ITEMS" -Fallback "25000")
AuctionHouseBot.Horde.MaxItems = $(Get-Setting -Name "AHBOT_HORDE_MAX_ITEMS" -Fallback "25000")
AuctionHouseBot.Neutral.MinItems = $(Get-Setting -Name "AHBOT_NEUTRAL_MIN_ITEMS" -Fallback "10000")
AuctionHouseBot.Neutral.MaxItems = $(Get-Setting -Name "AHBOT_NEUTRAL_MAX_ITEMS" -Fallback "10000")
AuctionHouseBot.Buyer.BuyCandidatesPerBuyCycle = $(Get-Setting -Name "AHBOT_BUY_CANDIDATES_PER_CYCLE" -Fallback "10")
AuctionHouseBot.Buyer.AcceptablePriceModifier = $(Get-Setting -Name "AHBOT_ACCEPTABLE_PRICE_MODIFIER" -Fallback "1")
"@

if ((Get-Setting "OLLAMA_CHAT_ENABLE" "0") -eq "1") {
    $playerbotsConfig += @"

AiPlayerbot.EnableBroadcasts = 0
AiPlayerbot.RandomBotTalk = 0
AiPlayerbot.RandomBotEmote = 0
AiPlayerbot.RandomBotSuggestDungeons = 0
AiPlayerbot.EnableGreet = 0
AiPlayerbot.GuildFeedback = 0
AiPlayerbot.RandomBotSayWithoutMaster = 0
"@
}
Set-Content -LiteralPath (Join-Path $ModuleConfigPath "playerbots.conf") -Value $playerbotsConfig -Encoding ascii
Set-Content -LiteralPath (Join-Path $ModuleConfigPath "mod_ahbot.conf") -Value $ahbotConfig -Encoding ascii

$dungeonClearConfig = @"
[worldserver]
DungeonClear.Enable = $(Get-Setting -Name "DUNGEON_CLEAR_ENABLE" -Fallback "1")
DungeonClear.BetterLootRolling = $(Get-Setting -Name "DUNGEON_CLEAR_BETTER_LOOT_ROLLING" -Fallback "1")
DungeonClear.LootMinQuality = $(Get-Setting -Name "DUNGEON_CLEAR_LOOT_MIN_QUALITY" -Fallback "1")
DungeonClear.RestHealthPct = $(Get-Setting -Name "DUNGEON_CLEAR_REST_HEALTH_PCT" -Fallback "85")
DungeonClear.RestManaPct = $(Get-Setting -Name "DUNGEON_CLEAR_REST_MANA_PCT" -Fallback "75")
"@

$autoBalanceConfig = @"
[worldserver]
AutoBalance.Enable.Global = $(Get-Setting -Name "AUTOBALANCE_ENABLE" -Fallback "1")
AutoBalance.LevelScaling = 1
AutoBalance.LevelScaling.Method = "dynamic"
AutoBalance.RewardScaling.Method = "dynamic"
AutoBalance.RewardScaling.XP = 1
AutoBalance.RewardScaling.XP.Modifier = 1.0
AutoBalance.RewardScaling.Money = 1
AutoBalance.RewardScaling.Money.Modifier = 1.0
AutoBalance.Enable.5M = 1
AutoBalance.Enable.10M = 1
AutoBalance.Enable.15M = 1
AutoBalance.Enable.20M = 1
AutoBalance.Enable.25M = 1
AutoBalance.Enable.40M = 1
AutoBalance.Enable.OtherNormal = 1
AutoBalance.Enable.5MHeroic = 1
AutoBalance.Enable.10MHeroic = 1
AutoBalance.Enable.25MHeroic = 1
AutoBalance.Enable.OtherHeroic = 1
AutoBalance.MinPlayers = $(Get-Setting -Name "AUTOBALANCE_MIN_PLAYERS" -Fallback "1")
AutoBalance.MinPlayers.Heroic = $(Get-Setting -Name "AUTOBALANCE_MIN_PLAYERS_HEROIC" -Fallback "1")
AutoBalance.MinPlayers.Raid = $(Get-Setting -Name "AUTOBALANCE_MIN_PLAYERS_RAID" -Fallback "1")
AutoBalance.MinPlayers.RaidHeroic = $(Get-Setting -Name "AUTOBALANCE_MIN_PLAYERS_RAID_HEROIC" -Fallback "1")
"@

$aoeLootConfig = @"
[worldserver]
AOELoot.Enable = $(Get-Setting -Name "AOE_LOOT_ENABLE" -Fallback "1")
AOELoot.Range = $(Get-Setting -Name "AOE_LOOT_RANGE" -Fallback "55.0")
AOELoot.Group = $(Get-Setting -Name "AOE_LOOT_GROUP" -Fallback "1")
AOELoot.MailEnable = 0
"@

$dungeonRespawnConfig = @"
[worldserver]
DungeonRespawn.Enable = $(Get-Setting -Name "DUNGEON_RESPAWN_ENABLE" -Fallback "1")
DungeonRespawn.RespawnHealthPct = $(Get-Setting -Name "DUNGEON_RESPAWN_HEALTH_PCT" -Fallback "50.0")
"@

$npcAllMountsConfig = @"
[worldserver]
AllMountsNPC.Announce = $(Get-Setting -Name "ALL_MOUNTS_NPC_ANNOUNCE" -Fallback "1")
AllMountsNPC.EnableAI = $(Get-Setting -Name "ALL_MOUNTS_NPC_ENABLE_AI" -Fallback "1")
AllMountsNPC.TeachBengalTiger = $(Get-Setting -Name "ALL_MOUNTS_NPC_TEACH_BENGAL_TIGER" -Fallback "0")
"@

$moneyForKillsConfig = @"
[worldserver]
MFK.Enable = $(Get-Setting -Name "MFK_ENABLE" -Fallback "1")
MFK.Announce = $(Get-Setting -Name "MFK_ANNOUNCE" -Fallback "0")
MFK.Announce.World.WorldBoss = $(Get-Setting -Name "MFK_ANNOUNCE_WORLD_BOSS" -Fallback "1")
MFK.Announce.World.Suicide = 0
MFK.Announce.Guild.Suicide = 0
MFK.Announce.Group.Suicide = 0
MFK.Announce.World.PvP = $(Get-Setting -Name "MFK_ANNOUNCE_WORLD_PVP" -Fallback "0")
MFK.Announce.Group.DungeonBoss = $(Get-Setting -Name "MFK_ANNOUNCE_GROUP_DUNGEON_BOSS" -Fallback "0")
MFK.Bounty.KillingBlowOnly = $(Get-Setting -Name "MFK_BOUNTY_KILLING_BLOW_ONLY" -Fallback "0")
MFK.Bounty.MoneyForNothing = $(Get-Setting -Name "MFK_BOUNTY_MONEY_FOR_NOTHING" -Fallback "0")
MFK.PVP.CorpseLootPercent = $(Get-Setting -Name "MFK_PVP_CORPSE_LOOT_PERCENT" -Fallback "0")
MFK.Bounty.Kill.Multiplier = $(Get-Setting -Name "MFK_BOUNTY_KILL_MULTIPLIER" -Fallback "10")
MFK.PVP.Kill.Multiplier = $(Get-Setting -Name "MFK_PVP_KILL_MULTIPLIER" -Fallback "0")
MFK.Bounty.DungeonBoss.Multiplier = $(Get-Setting -Name "MFK_BOUNTY_DUNGEON_BOSS_MULTIPLIER" -Fallback "25")
MFK.Bounty.WorldBoss.Multiplier = $(Get-Setting -Name "MFK_BOUNTY_WORLD_BOSS_MULTIPLIER" -Fallback "20")
MFK.Killer.Level.Diff.Enable = $(Get-Setting -Name "MFK_KILLER_LEVEL_DIFF_ENABLE" -Fallback "1")
MFK.Max.Gold.Threshold = $(Get-Setting -Name "MFK_MAX_GOLD_THRESHOLD" -Fallback "0.5")
"@

# Keep upstream prompt templates and command filters, then override our settings.
$ollamaTemplate = Join-Path $CorePath "modules/mod-ollama-chat/conf/mod_ollama_chat.conf.dist"
$ollamaConfig = [System.IO.File]::ReadAllText($ollamaTemplate)
$ollamaSettings = @{
    "Enable" = Get-Setting "OLLAMA_CHAT_ENABLE" "0"
    "Url" = Get-Setting "OLLAMA_CHAT_URL" "http://host.docker.internal:11434/api/generate"
    "Model" = Get-Setting "OLLAMA_CHAT_MODEL" "llama3.2:3b"
    "RateLimit.GlobalPerMinute" = Get-Setting "OLLAMA_CHAT_RATE_LIMIT_GLOBAL_PER_MINUTE" "20"
    "RateLimit.ScopePerMinute" = "6"
    "MaxConcurrentQueries" = "1"
    "WorkerThreads" = "1"
    "MaxQueueDepth" = "8"
    "HttpTimeoutSeconds" = "45"
    "NumCtx" = "4096"
    "NumPredict" = "80"
    "ThinkMode" = '"off"'
    "ThinkModeEnableForModule" = "0"
    "DisableForCustomChannels" = "0"
    "DisableForParty" = "0"
    "DisableRepliesInCombat" = Get-Setting "OLLAMA_CHAT_DISABLE_IN_COMBAT" "0"
    "EnableWhisperReplies" = "1"
    "EnableRandomChatter" = Get-Setting "OLLAMA_CHAT_RANDOM_CHATTER" "1"
    "EnableEventChatter" = "1"
    "Chatter.UseGeneralChannel" = "1"
    "Chatter.UseTradeChannel" = "1"
    "PlayerReplyChance.Channel" = "80"
    "PlayerReplyChance.Party" = "100"
    "MaxBotsToPick" = "1"
    "BotReplyChance.Channel" = "3"
    "BotReplyChance.Party" = "10"
    "BotConversation.MaxChainDepth" = "2"
    "BotConversation.RequireRecentHuman" = "1"
    "RandomChatterMaxBotsPerPlayer" = "1"
    "EventChatterMaxBotsPerPlayer" = "1"
    "MinRandomInterval" = "90"
    "MaxRandomInterval" = "240"
    "Cooldown.PerBotSeconds" = "45"
    "Cooldown.PerScopeSeconds" = "15"
}
foreach ($key in $ollamaSettings.Keys) {
    $pattern = '(?m)^OllamaChat\.' + [regex]::Escape($key) + '\s*=.*$'
    if (-not [regex]::IsMatch($ollamaConfig, $pattern)) {
        throw "Ollama config option no longer exists upstream: $key"
    }
    $replacement = "OllamaChat.$key = $($ollamaSettings[$key])"
    $ollamaConfig = [regex]::Replace($ollamaConfig, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $replacement })
}

Set-Content -LiteralPath (Join-Path $ModuleConfigPath "mod_dungeon_clear.conf") -Value $dungeonClearConfig -Encoding ascii
Set-Content -LiteralPath (Join-Path $ModuleConfigPath "AutoBalance.conf") -Value $autoBalanceConfig -Encoding ascii
Set-Content -LiteralPath (Join-Path $ModuleConfigPath "mod_aoe_loot.conf") -Value $aoeLootConfig -Encoding ascii
Set-Content -LiteralPath (Join-Path $ModuleConfigPath "dungeonrespawn.conf") -Value $dungeonRespawnConfig -Encoding ascii
Set-Content -LiteralPath (Join-Path $ModuleConfigPath "npc_allmounts.conf") -Value $npcAllMountsConfig -Encoding ascii
Set-Content -LiteralPath (Join-Path $ModuleConfigPath "mod_moneyforkills.conf") -Value $moneyForKillsConfig -Encoding ascii
[IO.File]::WriteAllText((Join-Path $ModuleConfigPath "mod_ollama_chat.conf"), $ollamaConfig, (New-Object Text.UTF8Encoding($false)))

$AccountSqlGenerator = Join-Path $PSScriptRoot "generate-accounts-sql.py"
# Prefer the Windows launcher over a possible Microsoft Store python shortcut.
$PythonCommand = Get-Command py -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $PythonCommand) {
    throw "Python is required to generate initial account SQL. Install Python or clear INITIAL_ACCOUNTS."
}

if ($PythonCommand.Name -eq "py.exe" -or $PythonCommand.Name -eq "py") {
    & $PythonCommand.Source -3 $AccountSqlGenerator
} else {
    & $PythonCommand.Source $AccountSqlGenerator
}

if ($LASTEXITCODE -ne 0) {
    throw "Failed to generate initial account SQL."
}

Write-Host "Wrote module configs to $ModuleConfigPath"
