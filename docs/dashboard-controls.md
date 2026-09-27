# Dashboard controls and monitoring

Open **http://127.0.0.1:8765/** on the Windows server PC. This native control
page stays available even when every Docker container and Ollama are stopped.
The existing **http://127.0.0.1:3000/** dashboard embeds the same controls and
retains the account/character statistics below them.

## One-click operation

Double-click **Start Server.cmd** or **Stop Server.cmd** in the project folder.
They start the local controller if needed, submit the operation and open its
progress page. PowerShell equivalents:

```powershell
.\scripts\start-all.ps1
.\scripts\stop-all.ps1 -Countdown 60
```

Start checks Docker Desktop (launching it if necessary), starts native Ollama
when chat is enabled, regenerates module config, then starts the Compose stack.
It uses existing images; use `scripts/start.ps1` for source changes requiring a
rebuild. Install Python 3 and the Ollama runtime first as described in
[GPU chat setup](ollama.md).

Stop announces a countdown in game, sends Docker's normal termination signal
and gives the world server up to 120 seconds to save/logout players and bots.
It then stops the other project containers and native Ollama. Account and model
data remain on disk. It does not quit Docker Desktop or affect unrelated projects.
The controller deliberately remains running so the Start button still works.

The default warning is 60 seconds; the UI accepts 10–300 seconds. Only one
operation may run at a time. The page shows countdown, saving/stopping stages,
completion and failure. If a start fails, services that already started remain
available for inspection; retry after fixing the reported error.

## Dashboard buttons

| Control | Behavior |
| --- | --- |
| Start game + Ollama | Start this project and native AI service. |
| Start world | Start world dependencies and native AI when enabled. |
| Stop world | Warn, save and stop only the world server. |
| Stop game + Ollama | Warn, save and stop the whole project plus native AI. |
| Save for next start | Validate and write .env, then regenerate config; no restart. |
| Save + restart world | Warn and stop world, save settings, then start with the new configuration. |
| Reload saved chat settings | Regenerate configuration and send `ollama reload` through the local console. |
| Test Ollama reply | Generate one short reply and record its response time. Does not post it in game. |

XP controls include kill, quest and Dungeon Finder quest rates (3x), plus
battleground kill and objective XP (5x). Battleground kill XP is enabled.
The battleground multiplier is independent of the ordinary kill rate.
Bot minimum
cannot exceed maximum. Changing bot targets does not instantly create or delete
all bot characters; the bot manager converges to its configured population.
Chat controls include enable/disable, ambient chatter, combat replies and the
global messages-per-minute cap. Unsaved form edits are never overwritten by
monitoring polls. Reload applies saved settings; XP and bot environment values
require container recreation through Save + restart or the next start.

`SYNC_LEVEL_WITH_PLAYERS=1` enables Playerbots' level limit for newly randomized
random bots, based on observed non-GM human levels with up to a three-level
headroom. The tracked cap rises during the server session. It does not immediately
relevel existing bots or continuously match party bots to your exact level;
death knights retain their starting-level minimum.

Dungeon AutoBalance explicitly enables dynamic creature-level, kill-XP and
money scaling. Repeat clears can therefore remain useful for XP and gold as
you level, with rewards adjusted for difficulty and party size. Item drops
retain their original item levels; ordinary quest completion rules, Dungeon
Finder first/repeat reward differences and instance lockouts still apply.
Check `.ab mapstat` and `.ab creaturestat` in game to inspect current scaling.

Quest-required, independent creature drops have a database-level 2.5x chance
boost, capped at 100%. Shared groups, reference loot and ordinary drops are
unchanged. This is separate from XP controls; see [Quest drop boost](modules.md#quest-drop-boost)
for scope and reapplication instructions.

## Monitoring

- **Realm readiness:** world container running, initialization confirmed in this
  boot's log, realm offline flag clear and the local world TCP port responding.
  This is a readiness check, not a simulated login.
- **Population:** online characters and bots belonging to Playerbots account
  types 1/2. Personal alt bots may count among other characters.
- **GPU:** highest current Windows GPU-engine utilization for the project's
  Ollama/runner processes. This is an engine sample, not whole-card utilization.
  Unavailable counters display unknown. Model VRAM comes from Ollama `/api/ps`;
  it excludes memory used by games and other applications. An idle model may unload.
- **Latency:** inexpensive API ping plus the last explicitly requested reply
  test. The latter is not an average of all in-game messages.
- **Logs:** the latest 100 lines from world, auth, database or native Ollama,
  polled every five seconds. Pause keeps the current window readable.
- **Errors:** monitoring failures and errors in the current recent-world-log
  window, plus operation history. This is not a permanent incident archive.

Status is collected about every five seconds plus collection time; the UI polls
the cached sample every two seconds. Check the sample timestamp if Docker is slow.
When stopped, realm status is offline and character counts are zero regardless
of stale database online flags. The older character tables below the embedded
controls are explicitly labeled as page-load snapshots.

## Local access and troubleshooting

The controller listens only on `127.0.0.1:8765`. The PHP dashboard proxies fixed
API routes through Docker Desktop's `host.docker.internal`. Actions require an
unguessable per-process token; Host/Origin checks reject remote web origins and
DNS rebinding. There is no arbitrary shell or console command endpoint. Neither
the Docker socket nor host filesystem is mounted into the PHP container.
Keep both dashboards local; this is a trusted-local-user tool, not a public
multi-user administration service.

After Windows restarts, use a one-click script or `scripts/start-control.ps1`.
If the embedded dashboard is offline, use port 8765. If that is unavailable,
inspect `var/control/stderr.log` and `var/control/commands.log`; failed commands
write diagnostics there. These local diagnostics may include sensitive server
configuration and should not be published. HTTP logs mask configured passwords.

The console transport requires Docker Desktop's local Linux named-pipe context.
It avoids SOAP credentials and does not open a remote administration port.
Configuration editing preserves unrelated `.env` keys and uses atomic replacement.
Changes to these controller Python files require restarting the controller when
no operation is in progress; dashboard PHP/HTML/JS changes require rebuilding
`ac-dashboard`. Python unit checks:

```powershell
py -3 -m unittest discover -s scripts/tests -v
```
