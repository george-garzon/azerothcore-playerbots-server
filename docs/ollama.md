# GPU-powered bot conversation

This host uses native Windows **Ollama 0.34.4**, its Vulkan backend and the
**AMD Radeon RX 9060 XT (16 GB)**. The tested `llama3.2:3b` model uses about
2.5 GB and reports **100% GPU**. The integrated Radeon GPU is excluded by
`GGML_VK_VISIBLE_DEVICES=1` in the startup script. If GPU enumeration changes,
check `var/ollama/serve.err.log` before changing that device index.

The game server stays in Docker and reaches Ollama through
`http://host.docker.internal:11434/api/generate`. Ollama binds only to Windows
localhost; Docker Desktop connectivity to that address has been tested. Do not
forward port 11434 through your router. The optional `llm` Docker profile is a
separate CPU-oriented alternative, not the GPU setup used here.

## Start

Run from the project folder:

```powershell
# First installation only: downloads the signed Windows runtime and model
.\scripts\start-ollama.ps1 -Install

# Subsequent starts (also ensures the model exists)
.\scripts\start-ollama.ps1

# Generate module settings, then start the game stack
.\scripts\apply-config.ps1
docker compose up -d
```

The runtime and models are stored under the Git-ignored `var/ollama/` folder.
The first download needs several GB of disk space. Ollama runs in the background
without opening a console window. Run the script again after a Windows reboot;
it does not install a system service or login task. An existing listener is
reused, so its GPU/environment settings are not changed by rerunning the script.

If the world server was already running when you regenerated config, enter
`.ollama reload` as a GM, or restart it with `docker compose restart ac-worldserver`.
The Playerbots canned-chatter settings need a world-server restart.

## Where bots talk

| Chat | How to use it | Conditions |
| --- | --- | --- |
| Global World | `/join World`, then use the channel number WoW assigns | Bots must already belong to that channel; Playerbots joins eligible non-solo random bots at level 10+. |
| General | Normal General channel | Eligible bots in the same channel/zone. |
| Trade | Normal Trade channel in a capital | Bots in the actual city Trade channel. |
| Dungeon party | `/p hello everyone` | Bots in your party; dungeon clear controls still work separately. |
| Raid | `/raid hello everyone` | Bots in your raid. |
| Battleground | `/bg hello team` | Bots on your battleground team/group. |
| Whisper | Whisper a bot by name | Whisper replies enabled; global rate limit still applies. |

Global here means the **World channel**, not a newly created channel named
Global. Ambient World chatter is added by the project patch. It requires an
eligible bot and a real listener; the module's other ambient eligibility and
nearby-player checks still apply. Do not expect every bot across the server to
continually broadcast. Trade and General retain normal channel membership rules.

The battleground patch recognizes both normal and leader BG messages. It routes
generated party/raid chatter through the bot's BG group as battleground chat,
not to the opposing team. These code paths compile successfully; actual
party/BG conversation still needs an in-game check with your character present.

Replies and ambient/event remarks use character and location context. Chat does
not add tactical AI abilities or guarantee accurate dungeon advice. Bot commands
are filtered so ordinary control messages do not trigger LLM conversation.

## Tuning

```dotenv
OLLAMA_CHAT_ENABLE=1
OLLAMA_CHAT_URL=http://host.docker.internal:11434/api/generate
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_CHAT_RATE_LIMIT_GLOBAL_PER_MINUTE=20
OLLAMA_CHAT_DISABLE_IN_COMBAT=0
OLLAMA_CHAT_RANDOM_CHATTER=1
```

Replies during combat are enabled for dungeon/BG use. Generated config also
limits concurrent inference to one worker, queue depth to eight, context to
4,096 tokens and replies to 80 generated tokens. Ambient checks run at random
90–240 second intervals; global/per-channel limits and cooldowns can skip lines.
The rate cap controls chat delivery; it is not a strict GPU workload quota.
Bot-to-bot replies have low probabilities and require recent human activity.

`apply-config.ps1` preserves upstream prompt templates, command filters and
defaults, then applies the project's overrides. While Ollama is enabled it
disables the Playerbots canned broadcasts, random talking and greeting features
recommended by the upstream module, reducing duplicate chatter.

To change model, run `start-ollama.ps1 -Model <model>`, update
`OLLAMA_CHAT_MODEL` in `.env`, regenerate config and reload/restart the module.
The tested 3B model leaves GPU memory available for the WoW client.

## Verify and troubleshoot

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/version
& .\var\ollama\runtime\ollama.exe ps
Get-Content .\var\ollama\serve.err.log -Tail 30
docker compose logs --tail 100 ac-worldserver
```

`ps` shows a model only after an inference request; after 30 idle minutes it may
unload from GPU memory. Look for `100% GPU` after a reply. CPU-only inference or
Vulkan errors warrant checking the device index and updating the AMD graphics
driver. Windows ROCm's supported-card list differs from Linux; this setup uses
the verified Vulkan path rather than assuming ROCm Docker passthrough.

For no replies, first whisper a bot using ordinary conversational text. Then
check the Ollama logs, module enabled state, model name, cooldowns, channel
membership and whether a real player is present. A successful API test alone
does not prove every in-game route is being exercised.

The patch is tracked in `scripts/patches/ollama-chat-channels.patch` and applied
by startup/bootstrap through `apply-module-compat.ps1`. After an upstream update
the script stops if the patch no longer applies, so it can be reviewed rather
than silently dropping the World/BG support. Local patched module changes may
also need reconciling before Git can pull an upstream update.

## Stop

```powershell
docker compose stop
.\scripts\stop-ollama.ps1
```

Docker stop does not stop the native Ollama process. To keep playing without AI
chat, set `OLLAMA_CHAT_ENABLE=0`, apply config and restart the world server before
stopping Ollama. Models and accounts are retained.

References: [Ollama GPU support](https://docs.ollama.com/gpu),
[Windows support](https://docs.ollama.com/windows),
[chat module](https://github.com/DustinHendrickson/mod-ollama-chat).
