# Installed module guide

These are the game-server plugins cloned by `scripts/bootstrap.ps1`. Client
addons are separate and must be installed on each gaming PC. See
[operations](operations.md) for applying `.env` changes and obtaining GM access.
Commands below are typed in game unless explicitly marked as PowerShell or SQL.

## Playerbots and MultiBot Bridge

`mod-playerbots` creates AI players. `BOT_MIN` and `BOT_MAX` control the online
random-bot target; defaults are 500. `RANDOM_BOT_MIN_LEVEL` and
`RANDOM_BOT_MAX_LEVEL` control the configured level range. `MAX_ADDED_BOTS`
limits controllable party bots. Lower the population if the host struggles.

Install [MultiBot Chatless](https://github.com/Wishmaster117/MultiBot-Chatless)
in the client's `Interface/AddOns` folder and enable it at character selection.
Use its roster, bot connection and group controls to manage your bots, then its
strategy, gear and talent controls as needed. The installed
`mod-multibot-bridge` supplies the server side; it displays no UI by itself.
Only bots the player is authorized to control are available through the bridge.

For chat control, start with `.help playerbots`; this build registers the
`.playerbots bot` command. Refer to the
[Playerbots wiki](https://github.com/mod-playerbots/mod-playerbots/wiki) for
the complete command syntax and supported dungeon/raid strategies.

`RANDOM_BOT_JOIN_LFG`, `RANDOM_BOT_JOIN_BG`, and `RANDOM_BOT_AUTO_JOIN_BG`
control dungeon-finder and battleground participation. Join through the normal
client interfaces. The `RANDOM_BOT_BG_*` settings control enabled brackets and
counts; bots still need suitable levels and eligible queues.

## Dungeon Clear

Form a party with a **bot tank**, enter a dungeon and run:

| Command | Action |
| --- | --- |
| `.dc on` | Let the tank lead the clear. |
| `.dc off` | Stop and return control to the player. |
| `.dc pause` | Pause or resume. |
| `.dc status` | Inspect the current run. |
| `.dc bosses` | List bosses and kill state. |
| `.dc skip` | Skip a stalled objective. |
| `.dc config` | Inspect effective module settings. |

The real player must be in the bot's group. A DPS/healer player can follow the
tank. The optional [Dungeon Clear addon](https://github.com/jrad7/mod-dungeon-clear-addon)
provides buttons for these controls. Configure `DUNGEON_CLEAR_ENABLE`,
`DUNGEON_CLEAR_BETTER_LOOT_ROLLING`, `DUNGEON_CLEAR_LOOT_MIN_QUALITY` and rest
thresholds in `.env`.

## AutoBalance

Scales instance creatures for the party. Enter a dungeon and use `.ab mapstat`
to inspect scaling or target a creature and use `.ab creaturestat`.
`AUTOBALANCE_ENABLE` toggles it; `AUTOBALANCE_MIN_PLAYERS` and the heroic/raid
variants set minimum scaling counts. Bots can affect the effective party size;
inspect the reported values before adjusting difficulty. GM `.ab setoffset`
changes the server-wide difficulty offset; `.ab getoffset` displays it.

## DungeonRespawn

Release spirit after dying in a dungeon to trigger the module's return to the
entrance and resurrection behavior. `DUNGEON_RESPAWN_ENABLE` toggles it and
`DUNGEON_RESPAWN_HEALTH_PCT` controls restored health (default 50). No activation
chat command is needed. Startup applies the callback compatibility fix for this core.

## Auction House Bot Plus

This needs a **regular, non-playerbot character** to own auctions.

1. Create a dedicated account through the world console with
   `account create AHOWNER <password>`.
2. Log in to that account and create a character, then log it out.
3. Open MySQL with `docker compose exec ac-database mysql -uroot -p acore_characters`
   and run `SELECT guid, name FROM characters WHERE name = 'YourAuctionCharacter';`.
4. Set `AHBOT_GUIDS` in `.env` to that GUID (comma-separated for multiple owners).
5. Apply configuration and restart the world server as described in operations.

Visit an auctioneer to check inventory. GM `.ahbot reload` reloads module
configuration; `.ahbot update` requests an auction refresh. Seller and buyer
switches are `AHBOT_ENABLE_SELLER` and `AHBOT_ENABLE_BUYER`. Tune listing targets
with `AHBOT_ALLIANCE_*`, `AHBOT_HORDE_*`, `AHBOT_NEUTRAL_*` and
`AHBOT_ITEMS_PER_CYCLE`. An `AHBOT_GUIDS` value of 0 is not a working auction owner.

## AoE Loot

Loot a corpse normally to collect eligible nearby loot. Configure
`AOE_LOOT_ENABLE`, `AOE_LOOT_RANGE` and `AOE_LOOT_GROUP` in `.env`.
Group loot and item eligibility still matter; this does not grant ownership of
every nearby corpse. The generated configuration disables mail delivery.

## Money for Kills

Rewards eligible kills automatically. `MFK_ENABLE` enables it;
`MFK_BOUNTY_KILL_MULTIPLIER`, `MFK_BOUNTY_DUNGEON_BOSS_MULTIPLIER` and
`MFK_BOUNTY_WORLD_BOSS_MULTIPLIER` tune payouts. These are money settings,
independent of the 3x XP rates. `MFK_PVP_CORPSE_LOOT_PERCENT=0` keeps corpse-based
PvP money theft disabled. No player command is needed.

## All Mounts NPC

A GM can place the mount teacher at their current position:

```text
.npc add 601014
```

Talk to the NPC and use its gossip options to learn mounts. This creates a
persistent spawn, so avoid repeating it at the same location.
`ALL_MOUNTS_NPC_ENABLE_AI` enables the teacher;
`ALL_MOUNTS_NPC_TEACH_BENGAL_TIGER` controls the optional Bengal Tiger.

## Transmogrification

A GM can place the appearance NPC with `.npc add 190010`. Players talk to it
to change equipment appearances according to the module's restrictions and costs.
For custom rules, copy the module's `conf/transmog.conf.dist` to
`azerothcore-wotlk/env/dist/etc/modules/transmog.conf`, edit and restart.
There is no project `.env` toggle for this module.

## Individual Progression

Progress through expansion/content tiers by completing their requirements.
Higher-tier access can remain locked despite fast leveling; 3x XP does not
bypass progression. Use the upstream
[tier guide](https://github.com/ZhengPeiRu21/mod-individual-progression/wiki/List-of-Progression-Tiers)
to identify the next requirement.

Configure `individualProgression.conf` using the module's distributed template.
`IndividualProgression.Enable` controls it. The upstream module requires
`EnablePlayerSettings = 1` in `worldserver.conf` to save progress and recommends
`DBC.EnforceItemAttributes = 0` for its item-stat overrides. Check these when
troubleshooting progression. It has no generated `.env` settings in this project.

## Capital portals

Look near the portal trainers in capital cities. This package is SQL-only:
cloning it alone does not install the portal spawns, and its root-level SQL is
not part of the standard module SQL directory layout.

If portals are absent, back up `acore_world`, review
`azerothcore-wotlk/modules/portals-in-all-capitals/portals-in-all-capitals.up.sql`
for ID conflicts, then import it once:

```powershell
docker compose cp ./azerothcore-wotlk/modules/portals-in-all-capitals/portals-in-all-capitals.up.sql ac-database:/tmp/capital-portals.sql
docker compose exec ac-database mysql -uroot -p acore_world
```

At the MySQL prompt run `source /tmp/capital-portals.sql;`, then `exit` and
restart the world server. The companion `.down.sql` removes these changes;
review it before using it. There is no `.env` toggle.

## Ollama Chat (optional)

Provides generated conversation in World, General, Trade, parties, raids and
battlegrounds. The RX 9060 XT setup uses native Windows Ollama with Vulkan:

```powershell
.\scripts\start-ollama.ps1
.\scripts\apply-config.ps1
```

The `.env` selects `llama3.2:3b` at
`http://host.docker.internal:11434/api/generate`. Start/restart the world server
after applying settings. See [GPU chat setup](ollama.md) for first installation,
channel eligibility, chat limits and GPU verification. Disable with
`OLLAMA_CHAT_ENABLE=0`, apply config and restart. The native service is stopped
separately with `.\scripts\stop-ollama.ps1`.

## ALE Lua engine

Runs server-side Lua scripts. Place trusted `.lua` scripts under `scripts/lua/`;
Compose mounts this into the worldserver's Lua scripts directory. Restart the
world server and inspect logs for loading errors. The folder initially contains
only `.gitkeep`, not gameplay scripts. For engine options, create
`mod_ale.conf` from its distributed template; `ALE.Enabled` toggles the engine.

## Upstream reference

Each installed module's README and `conf/*.conf.dist` under
`azerothcore-wotlk/modules` document its full options. This guide covers the
checked-out modules; commands and defaults can change after source updates.
