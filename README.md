# AzerothCore + Playerbots Solo Stack

Docker-based AzerothCore WotLK using the latest compatible Playerbot fork plus a solo-friendly module set for LFG dungeons, battlegrounds, auction house economy, progression, and quality-of-life play.

The important bit: `mod-playerbots` requires the `mod-playerbots/azerothcore-wotlk` `Playerbot` branch. The vanilla AzerothCore repo will not build with that module.

## Quick Start

See [server operations](docs/operations.md) for start/stop, networking and XP
settings, and [module guide](docs/modules.md) for operating the installed plugins.

Kill and quest XP default to **3x**, including Dungeon Finder quest rewards.

```powershell
Copy-Item .env.example .env
notepad .env
.\scripts\bootstrap.ps1
docker compose up -d --build
```

The first build and database import can take a while. The default `.env.example` is tuned for 500 random bots:

```dotenv
BOT_MIN=500
BOT_MAX=500
RANDOM_BOT_JOIN_LFG=1
RANDOM_BOT_JOIN_BG=1
RANDOM_BOT_AUTO_JOIN_BG=1
```

It also seeds these login accounts after the auth DB import:

```dotenv
INITIAL_ACCOUNTS=george:password,harper:password,colby:password,isaac:password
```

Account names are uppercased by AzerothCore at creation time, so either `george` or `GEORGE` works at login. Existing accounts are not overwritten on later starts.

If you add more names to `INITIAL_ACCOUNTS` after the first run:

```powershell
.\scripts\apply-config.ps1
docker compose up --force-recreate ac-seed-accounts
```

## What Gets Installed

- `mod-playerbots/azerothcore-wotlk`, branch `Playerbot`
- `mod-playerbots/mod-playerbots`, branch `master`
- `jrad7/mod-dungeon-clear`, branch `master`
- `azerothcore/mod-autobalance`, branch `master`
- `NathanHandley/mod-ah-bot-plus`, branch `master`
- `ZhengPeiRu21/mod-individual-progression`, branch `master`
- `azerothcore/mod-transmog`, branch `master`
- `azerothcore/mod-aoe-loot`, branch `master`
- `AnchyDev/DungeonRespawn`, branch `master`
- `azerothcore/mod-npc-all-mounts`, branch `master`
- `azerothcore/mod-money-for-kills`, branch `master`
- `Wishmaster117/mod-multibot-bridge`, branch `main`
- `azerothcore/portals-in-all-capitals`, branch `main`
- `DustinHendrickson/mod-ollama-chat`, branch `main`
- `azerothcore/mod-ale`, branch `master`
- A Docker service that creates the required `acore_playerbots` database before import/startup
- A Docker service that creates the initial friend login accounts after auth DB import
- A localhost-only observer dashboard at `http://127.0.0.1:3000`

## Solo Dungeons And BGs

The generated `playerbots.conf` enables:

- random bots joining LFG
- random bots joining BGs
- automatic bot-filled Warsong Gulch, Arathi Basin, and Eye of the Storm at level 80 brackets by default
- dungeon/raid instance strategies
- 40 controllable party bots for larger group experiments

For autonomous dungeon clears, make a party with a bot tank, enter a dungeon, then use:

```text
.dc on
```

or install the companion addon from `mod-dungeon-clear` for in-game buttons. The tank must be a bot; play a DPS/healer/follower character unless you intentionally use self-bot mode.

`DungeonRespawn` is also enabled by default. If you die inside a dungeon, it respawns you at the dungeon start with:

```dotenv
DUNGEON_RESPAWN_HEALTH_PCT=50.0
```

## Local Observer Dashboard

The stack includes a read-only PHP dashboard inspired by the WebTerminal idea, but scoped to localhost stats instead of exposing a command terminal.

Open it after the stack is up:

```text
http://127.0.0.1:3000
```

It shows:

- online/total accounts and characters
- seeded friend account status
- configured bot count, LFG, BG, AoE loot, DungeonRespawn, all-mounts NPC, money-for-kills, AutoBalance, and AHBot settings
- auction listing count, guild count, faction split, class split, world uptime, and server ports
- JSON output at `http://127.0.0.1:3000/?format=json`

Docker binds the dashboard to `127.0.0.1` only:

```yaml
127.0.0.1:${DASHBOARD_EXTERNAL_PORT:-3000}:80
```

Change the local port in `.env` if needed:

```dotenv
DASHBOARD_EXTERNAL_PORT=3000
```

## Extra Solo-Friendly Plugins

The all-mounts NPC and money-for-kills modules are included by default:

```dotenv
ALL_MOUNTS_NPC_ANNOUNCE=1
ALL_MOUNTS_NPC_ENABLE_AI=1
ALL_MOUNTS_NPC_TEACH_BENGAL_TIGER=0

MFK_ENABLE=1
MFK_BOUNTY_KILL_MULTIPLIER=10
MFK_BOUNTY_DUNGEON_BOSS_MULTIPLIER=25
MFK_BOUNTY_WORLD_BOSS_MULTIPLIER=20
MFK_PVP_CORPSE_LOOT_PERCENT=0
```

`MFK_PVP_CORPSE_LOOT_PERCENT` is intentionally `0` so battlegrounds and friend duels do not steal gold from players.

## Running And Updating

Start or rebuild:

```powershell
.\scripts\start.ps1
```

Startup and bootstrap apply the DungeonRespawn player-hook compatibility fix for
the current Playerbot core. If building directly with Compose after fetching
modules manually, apply it first:

```powershell
.\scripts\apply-module-compat.ps1
docker compose up -d --build
```

After changing bot/module settings in `.env`, run:

```powershell
.\scripts\apply-config.ps1
docker compose restart ac-worldserver
```

Pull the latest compatible core and module code:

```powershell
.\scripts\update.ps1
docker compose up -d --build
```

Attach to the worldserver console:

```powershell
docker attach ac-worldserver
```

Detach without stopping it with `Ctrl+P`, then `Ctrl+Q`.

## Auction House Bot

AHBot-plus is included and enabled, but it cannot actually trade until it has at least one real character GUID to act as. Do not use a playerbot character for this. After the server is up:

1. Create an AH bot account in the worldserver console.
2. Log in with a 3.3.5a client and create a character on that account.
3. Find that character GUID:

```powershell
$dbPassword = (Get-Content .env | Where-Object { $_ -match '^DOCKER_DB_ROOT_PASSWORD=' }) -replace '^DOCKER_DB_ROOT_PASSWORD=', ''
docker compose exec ac-database mysql -uroot -p"$dbPassword" acore_characters -e "SELECT guid, name, account FROM characters;"
```

4. Put one or more GUIDs in `.env`:

```dotenv
AHBOT_GUIDS=456
```

Restart the worldserver:

```powershell
docker compose restart ac-worldserver
```

## Ollama Chat

Bot conversation uses native Windows Ollama on the RX 9060 XT through Vulkan,
with `llama3.2:3b`. See the [GPU chat guide](docs/ollama.md) for installation,
World/Trade/dungeon/BG chat, rate limits, GPU checks and stopping Ollama.

```powershell
.\scripts\start-ollama.ps1
.\scripts\apply-config.ps1
docker compose up -d
```
