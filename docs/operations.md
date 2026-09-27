# Server operations

Run these PowerShell commands from the project folder. Docker Desktop must be
running with Linux containers.

For GPU bot chat, start native Ollama with `.\scripts\start-ollama.ps1` before
the game server. See [GPU chat operations](ollama.md); stopping Docker does not
stop the native Ollama process.

## Start and stop

Recommended: double-click `Start Server.cmd` / `Stop Server.cmd`, or use the
[control dashboard](dashboard-controls.md). They manage native Ollama alongside
Docker and warn players before stopping. The direct Docker commands below bypass
that countdown and do not manage native Ollama.

```powershell
# Start or apply Compose/.env changes without rebuilding images
docker compose up -d

# Stop all services, preserving accounts and characters
docker compose stop

# Resume existing containers without applying configuration changes
docker compose start

# Check status and follow game-server logs (Ctrl+C exits the log viewer)
docker compose ps -a
docker compose logs -f ac-worldserver
```

For initial setup or source changes, use `.\scripts\start.ps1`.
It applies configuration and builds the images. A rebuild is
not needed for XP or module configuration changes.

For a planned shutdown with players online, attach with `docker attach
ac-worldserver`, enter `server shutdown 60` to give a 60-second warning, then
detach with **Ctrl+P, Ctrl+Q**. Run `docker compose stop` once shutdown completes;
the world's restart policy otherwise starts it again. Do not use Ctrl+C to detach.

`docker compose down` removes containers but preserves named database volumes.
Do not add `-v` unless you intend to delete stored data.

## Experience rates

The project `.env` contains:

```dotenv
XP_RATE_KILL=3
XP_RATE_QUEST=3
XP_RATE_QUEST_DF=3
XP_RATE_BG=5
```

These map to AzerothCore's `Rate.XP.Kill`, `Rate.XP.Quest`, and
`Rate.XP.Quest.DF`. Dungeon Finder quest rewards have a separate rate, not an
additional multiplier on top of ordinary quest XP. `XP_RATE_BG` sets all six
battleground kill rates and the objective bonus rate to 5x; kill XP is enabled.
Exploration and pet XP remain at their existing settings. Normal level,
eligibility, group and progression rules still apply.

Apply edits on a running stack with:

```powershell
docker compose up -d --no-deps ac-worldserver
```

This may recreate the world container and disconnect players. If the entire
stack is stopped, use `docker compose up -d` instead. `restart` and `start` alone
do not load changed Compose environment variables.

## Module settings

See the [module guide](modules.md). Settings exposed in `.env` are written to
`azerothcore-wotlk/env/dist/etc/modules` by:

```powershell
.\scripts\apply-config.ps1
docker compose up -d
docker compose restart ac-worldserver
```

The restart loads generated files even when Compose did not recreate the
container. These commands start the stack if it was stopped. Editing a generated
module file directly is temporary: the next `apply-config.ps1` overwrites it.

For modules without a generated config, copy their `conf/*.conf.dist` from
`azerothcore-wotlk/modules/<module>` to `env/dist/etc/modules` under the core
directory, remove the `.dist` suffix, edit and restart the world server. Keep
the `[worldserver]` section header. Check the startup log for missing files.

## Console and administrator commands

```powershell
docker attach ac-worldserver
```

Console commands omit the leading dot used in game. To grant a trusted account
GM access, enter `account set gmlevel USERNAME 3 -1` in that console, then log
the account out and back in. This grants administrator privileges on all realms.
Only grant it to accounts that should administer the server. Use `help` for the
installed command list; in game use `.help`.

## Connecting

Use a WoW **3.3.5a build 12340** client and launch `Wow.exe`. Enter the server
username, even if the login field says email. Edit `Data/<locale>/realmlist.wtf`:

```text
set realmlist 136.227.250.162
```

This is the requested public endpoint. Forward TCP **3724** and **8085** to
the host's current LAN address (last checked: **192.168.4.117**) and allow those
ports in Windows Firewall. Keep the database, SOAP and dashboard ports private.
Public-IP access from inside the house requires router NAT loopback. Home
clients can use `192.168.4.117` instead. `192.168.150.1` is a VMware adapter on
this host, not its home-network address.

The realm database advertises where clients connect after authentication.
Inspect it with:

```powershell
docker compose exec ac-database mysql -uroot -p acore_auth
```

Enter `DOCKER_DB_ROOT_PASSWORD` from `.env`, then:

```sql
SELECT id, name, address, localAddress, port, flag FROM realmlist;
```

`address` is the public endpoint; `localAddress` is the LAN endpoint. An offline
realm requires checking world-server logs, not manually clearing its offline flag.

## Dashboard and troubleshooting

Open <http://127.0.0.1:3000> on the Docker host for embedded controls and character
statistics, or <http://127.0.0.1:8765> for controls that remain available while
Docker is stopped. See [dashboard controls](dashboard-controls.md).

- **Realm offline:** check `docker compose ps -a` and world-server logs. Initial
  database import and bot creation can take time.
- **Playerbots SQL directory missing:** the world service needs the read-only
  Playerbots SQL mount in `docker-compose.yml`; recreate it with Compose.
- **DungeonRespawn callback build failure:** run
  `.\scripts\apply-module-compat.ps1`, then rebuild. Startup/bootstrap also apply it.
- **Connected but no character screen:** confirm client build, realm address,
  both forwarded ports and access from the actual gaming PC.
- **Ollama connection errors:** see the optional Ollama section in the module guide.

Back up the databases before source updates or manually importing module SQL.
Existing account passwords are not changed by editing `INITIAL_ACCOUNTS`.
