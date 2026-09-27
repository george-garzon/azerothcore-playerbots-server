"""Local, fixed-action controller for this server. No external Python packages."""
import argparse
import collections
import datetime
import http.server
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.Lock()
STATE = {"job": None, "events": [], "probe": None}
LIMITS = {"XP_RATE_KILL": (0.1, 100), "XP_RATE_QUEST": (0.1, 100),
          "XP_RATE_QUEST_DF": (0.1, 100), "XP_RATE_BG": (0.1, 100), "BOT_MIN": (0, 5000), "BOT_MAX": (0, 5000),
          "OLLAMA_CHAT_ENABLE": (0, 1), "OLLAMA_CHAT_RATE_LIMIT_GLOBAL_PER_MINUTE": (1, 120),
          "OLLAMA_CHAT_DISABLE_IN_COMBAT": (0, 1), "OLLAMA_CHAT_RANDOM_CHATTER": (0, 1)}
DEFAULTS = dict(zip(LIMITS, [3, 3, 3, 5, 500, 500, 1, 20, 0, 1]))
CACHE = {"sampled_at": None, "errors": ["Collecting first sample..."]}
READY_BOOT = None
BOT_LEVEL_SYNC = {"next_check": 0, "applied": None}
BOT_LEVEL_DEFAULTS = {"BOT_LEVEL_MODE": "follow", "BOT_LEVEL_MIN": "1", "BOT_LEVEL_MAX": "24"}


def validate_bot_levels(values):
    if not isinstance(values, dict) or set(values) != set(BOT_LEVEL_DEFAULTS):
        raise ValueError("Provide the level mode, minimum and maximum.")
    if values["BOT_LEVEL_MODE"] not in ("follow", "manual"):
        raise ValueError("Select daily following or a manual range.")
    for key in ("BOT_LEVEL_MIN", "BOT_LEVEL_MAX"):
        if not re.fullmatch(r"[0-9]{1,2}", str(values[key])) or not 1 <= int(values[key]) <= 80:
            raise ValueError("Bot levels must be whole numbers between 1 and 80.")
    if int(values["BOT_LEVEL_MIN"]) > int(values["BOT_LEVEL_MAX"]):
        raise ValueError("Minimum bot level cannot exceed maximum.")
    return {key: str(value) for key, value in values.items()}


def run(args, timeout=60, input=None):
    # A launched background Ollama process can inherit pipe handles. File-backed
    # output lets the launcher finish without waiting for that long-lived child.
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(args, cwd=ROOT, input=input, stdout=output, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        output.seek(0)
        captured = output.read().decode("utf-8", "replace")
    if result.returncode:
        log_dir = ROOT / "var/control"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "commands.log").open("a", encoding="utf-8") as log:
            log.write(f"\n{args[0]} {args[1]} exit={result.returncode}\n{captured}\n")
        # Do not return arbitrary process output: configuration may contain credentials.
        raise RuntimeError(f"{args[0]} {args[1]} failed (exit {result.returncode}). Check local controller logs.")
    return captured


def compose(*args, **kwargs):
    return run(["docker", "compose", *args], **kwargs)


def ps_script(name, *args, timeout=180):
    return run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(ROOT / "scripts" / name), *args], timeout=timeout)


def env_values():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('\"').strip("'")
    return values


def validate_settings(values):
    if not isinstance(values, dict) or set(values) != set(LIMITS):
        raise ValueError("Provide exactly the supported settings.")
    cleaned = {}
    for key, (low, high) in LIMITS.items():
        raw = values[key]
        if isinstance(raw, bool) or not re.fullmatch(r"\d+(?:\.\d+)?", str(raw)):
            raise ValueError(f"Invalid number for {key}")
        number = float(raw)
        if not low <= number <= high or (not key.startswith("XP_") and not number.is_integer()):
            raise ValueError(f"{key} must be between {low} and {high}; counts must be integers.")
        cleaned[key] = format(number, "g")
    if int(cleaned["BOT_MIN"]) > int(cleaned["BOT_MAX"]):
        raise ValueError("Minimum bots cannot exceed maximum bots.")
    return cleaned


def save_settings(values):
    path = ROOT / ".env"
    original = path.read_text(encoding="utf-8-sig")
    lines, seen = [], set()
    for line in original.splitlines():
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else ""
        if key in values:
            if key in seen:
                continue
            line = f"{key}={values[key]}"
            seen.add(key)
        lines.append(line)
    lines.extend(f"{key}={value}" for key, value in values.items() if key not in seen)
    temp = path.with_suffix(".env.tmp")
    temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(temp, path)


def event(message):
    with LOCK:
        STATE["events"] = (STATE["events"] + [{"time": datetime.datetime.now().isoformat(timespec="seconds"),
                                               "message": message}])[-30:]


def stage(message, remaining=None):
    with LOCK:
        STATE["job"].update(message=message, remaining=remaining)


def inspect_world():
    try:
        return json.loads(run(["docker", "inspect", "ac-worldserver"], timeout=8))[0]
    except (RuntimeError, ValueError):
        return None


def console(command):
    # Named-pipe attach works without a terminal and adds no public admin port.
    return run([sys.executable, str(ROOT / "scripts/control_console.py"), command], timeout=10)


def countdown(seconds):
    world = inspect_world()
    if not world or not world["State"]["Running"]:
        return
    # Do not issue a world shutdown command: Docker's restart policy would restart it.
    # Announce a countdown, then let docker stop send SIGTERM for a clean save.
    deadline = time.monotonic() + seconds
    announced = set()
    while (remaining := max(0, int(deadline - time.monotonic() + 0.999))) > 0:
        stage("Players are being warned before shutdown", remaining)
        if (remaining == seconds or remaining in (60, 30, 10, 5)) and remaining not in announced:
            console(f"announce Server shutdown in {remaining} seconds. Please finish safely.")
            announced.add(remaining)
        time.sleep(min(0.25, max(0, deadline - time.monotonic())))


def ollama(path, payload=None, timeout=3):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request("http://127.0.0.1:11434" + path, data=data,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def perform(action, body):
    if action in ("save_bot_levels", "apply_bot_levels", "spread_bot_levels"):
        live = action != "save_bot_levels"
        if live:
            world = inspect_world()
            if not world or not world["State"]["Running"]:
                raise RuntimeError("World is stopped. Use Save for next start.")
        settings = {**body["settings"], "BOT_LEVEL_MATCH_ENABLE": "1",
                    "BOT_LEVEL_SPREAD": "1" if action == "spread_bot_levels" else "0"}
        if settings["BOT_LEVEL_MODE"] == "follow" and env_values().get("BOT_LEVEL_MATCH_GUID", "0") == "0":
            raise ValueError("Configure a human character GUID before enabling daily following.")
        save_settings(settings)
        ps_script("apply-config.ps1")
        if live:
            stage("Applying bot brackets; eligible bots adjust gradually when safe")
            output = console("reload config")
            if "Level management config reloaded." not in output:
                raise RuntimeError("Settings saved, but live reload was not confirmed.")
        return
    if action in ("start_all", "start_world"):
        stage("Checking Docker Desktop")
        ps_script("start-docker.ps1")
        stage("Starting Ollama and applying configuration")
        values = env_values()
        if values.get("OLLAMA_CHAT_ENABLE", "1") == "1":
            ps_script("start-ollama.ps1", "-Model", values.get("OLLAMA_CHAT_MODEL", "llama3.2:3b"), timeout=900)
        ps_script("apply-config.ps1")
        stage("Starting Docker services")
        compose("up", "-d", *([] if action == "start_all" else ["ac-worldserver"]), timeout=600)
        stage("Containers started; waiting for realm readiness")
        return
    if action in ("stop_all", "stop_world", "apply_settings"):
        countdown(body["countdown"])
        stage("Saving players and stopping world server")
        compose("stop", "-t", "120", "ac-worldserver", timeout=150)
        if action == "stop_all":
            stage("Stopping Docker services and native Ollama")
            compose("stop", "-t", "60", timeout=180)
            ps_script("stop-ollama.ps1")
        elif action == "apply_settings":
            save_settings(body["settings"])
            ps_script("apply-config.ps1")
            if body["settings"]["OLLAMA_CHAT_ENABLE"] == "1":
                ps_script("start-ollama.ps1", "-Model", env_values().get("OLLAMA_CHAT_MODEL", "llama3.2:3b"), timeout=900)
            stage("Starting world with saved settings")
            compose("up", "-d", "ac-worldserver", timeout=600)
    elif action == "save_settings":
        save_settings(body["settings"])
        ps_script("apply-config.ps1")
    elif action == "reload_chat":
        world = inspect_world()
        if not world or not world["State"]["Running"]:
            raise RuntimeError("World server is stopped. Start it to reload chat.")
        ps_script("apply-config.ps1")
        console("ollama reload")
    elif action == "probe":
        stage("Measuring one Ollama reply")
        begin = time.monotonic()
        result = ollama("/api/generate", {"model": env_values().get("OLLAMA_CHAT_MODEL", "llama3.2:3b"),
                        "prompt": "Say hello to a dungeon party in one short sentence.", "stream": False,
                        "options": {"num_ctx": 4096, "num_predict": 40}}, timeout=90)
        if not result.get("response"):
            raise RuntimeError("Ollama returned an empty reply.")
        with LOCK:
            STATE["probe"] = {"seconds": round(time.monotonic() - begin, 2),
                              "tokens": result.get("eval_count"), "time": time.time()}


ACTIONS = {"start_all", "start_world", "stop_all", "stop_world", "save_settings", "apply_settings", "reload_chat", "probe"}
ACTIONS.update({"save_bot_levels", "apply_bot_levels", "spread_bot_levels"})


def submit(action, body):
    if not isinstance(action, str) or action not in ACTIONS:
        raise ValueError("Unknown action")
    if action in ("stop_all", "stop_world", "apply_settings"):
        seconds = body.get("countdown", 60)
        if type(seconds) is not int or not 10 <= seconds <= 300:
            raise ValueError("Countdown must be 10 to 300 seconds.")
        body["countdown"] = seconds
    if action in ("save_settings", "apply_settings"):
        body["settings"] = validate_settings(body.get("settings"))
    if action in ("save_bot_levels", "apply_bot_levels", "spread_bot_levels"):
        body["settings"] = validate_bot_levels(body.get("settings"))
    with LOCK:
        if STATE["job"] and STATE["job"]["status"] == "running":
            raise RuntimeError("Another operation is running.")
        STATE["job"] = {"action": action, "status": "running", "message": "Starting", "remaining": None}

    def work():
        try:
            event(f"Started {action}")
            perform(action, body)
            with LOCK:
                STATE["job"].update(status="complete", message="Operation completed", remaining=None)
            event(f"Completed {action}")
        except Exception as exc:
            message = str(exc)
            with LOCK:
                STATE["job"].update(status="failed", message=message, remaining=None)
            event(f"Failed {action}: {message}")
    threading.Thread(target=work, daemon=True).start()


def tail(path, count=100):
    if not path.exists():
        return "No log file yet."
    with path.open("rb") as source:
        source.seek(max(0, path.stat().st_size - 64000))
        return "\n".join(source.read().decode("utf-8", "replace").splitlines()[-count:])


def logs(source):
    if source == "ollama":
        text = tail(ROOT / "var/ollama/serve.err.log")
    elif source in ("ac-worldserver", "ac-authserver", "ac-database"):
        result = subprocess.run(["docker", "compose", "logs", "--no-color", "--tail", "100", source],
                                cwd=ROOT, capture_output=True, timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        text = (result.stdout + result.stderr).decode("utf-8", "replace")
    else:
        raise ValueError("Unsupported log source")
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    # Mask local credentials if any dependency accidentally logs them.
    for key, value in env_values().items():
        if any(part in key for part in ("PASSWORD", "TOKEN", "SECRET")) and value:
            text = text.replace(value, "[redacted]")
    return text[-48000:]


def sql(query):
    return compose("exec", "-T", "ac-database", "sh", "-c",
                   'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot -N -B',
                   input=query, timeout=8).strip()


def collect():
    global READY_BOOT
    result = {"sampled_at": time.time(), "errors": [], "realm": "offline", "online": None,
              "bots": None, "ollama": {"online": False}, "gpu_utilization": None, "services": []}
    try:
        raw = compose("ps", "-a", "--format", "json", timeout=8).strip()
        services = json.loads(raw) if raw.startswith("[") else [json.loads(line) for line in raw.splitlines() if line]
        result["services"] = [{"name": s["Service"], "state": s["State"], "status": s.get("Status", "")} for s in services]
        world = next((s for s in services if s["Service"] == "ac-worldserver"), {})
        running = world.get("State") == "running"
        initialized = False
        if running:
            details = inspect_world()
            boot = details["State"]["StartedAt"] if details else None
            if boot and READY_BOOT != boot:
                startup_log = compose("logs", "--no-color", "--since", boot, "ac-worldserver", timeout=8)
                if "WORLD: World Initialized In" in startup_log:
                    READY_BOOT = boot
            initialized = bool(boot and READY_BOOT == boot)
            recent = logs("ac-worldserver")
            result["recent_errors"] = [line for line in recent.splitlines()
                                       if re.search(r"\berror\b|\bfailed\b|\bfatal\b", line, re.I)][-8:]
        else:
            result["online"] = result["bots"] = 0
        if any(s["Service"] == "ac-database" and s["State"] == "running" for s in services):
            realm = sql("SELECT address,flag FROM acore_auth.realmlist WHERE id=1;").split("\t")
            result["realm_address"] = realm[0] if realm else None
            flags = int(realm[1]) if len(realm) > 1 else 2
            port = int(env_values().get("DOCKER_WORLD_EXTERNAL_PORT", "8085"))
            ready = False
            if running:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        ready = initialized and not flags & 2
                except OSError:
                    pass
            result["realm"] = "ready" if ready else ("starting" if running else "offline")
            counts = sql("SELECT COUNT(*),COALESCE(SUM(t.account_type IN (1,2)),0) FROM acore_characters.characters c LEFT JOIN acore_playerbots.playerbots_account_type t ON t.account_id=c.account WHERE c.online=1;").split("\t")
            result["online"], result["bots"] = map(int, counts)
            if not running:
                result["online"] = result["bots"] = 0
    except Exception as exc:
        result["errors"].append(str(exc))
    try:
        begin = time.monotonic()
        info = ollama("/api/ps")
        result["ollama"] = {"online": True, "api_ms": round((time.monotonic() - begin) * 1000),
                            "models": [{"name": m["name"], "vram": m.get("size_vram", 0), "size": m.get("size", 0)} for m in info.get("models", [])]}
    except Exception:
        result["errors"].append("Ollama is stopped or unreachable.")
    try:
        result["gpu_utilization"] = float(ps_script("gpu-usage.ps1", timeout=8).strip())
    except Exception:
        pass  # Unsupported/localized counters are unknown, never a fabricated 0%.
    return result


def sync_bot_level(sample):
    """Follow the explicitly selected human; retain the core's bot safety exclusions."""
    values = env_values()
    guid = values.get("BOT_LEVEL_MATCH_GUID", "0")
    if (values.get("BOT_LEVEL_MATCH_ENABLE") != "1" or values.get("BOT_LEVEL_MODE", "follow") == "manual"
            or guid == "0" or sample.get("realm") != "ready"):
        return
    if not guid.isdecimal() or int(guid) < 1:
        raise ValueError("BOT_LEVEL_MATCH_GUID must identify a human character.")
    schedule_path = ROOT / "var/control/bot-level-sync.json"
    if BOT_LEVEL_SYNC["applied"] is None and schedule_path.exists():
        try:
            schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
            if schedule.get("guid") == guid and schedule.get("level") == values.get("BOT_LEVEL_MATCH_TARGET"):
                BOT_LEVEL_SYNC["next_check"] = max(BOT_LEVEL_SYNC["next_check"], float(schedule["next_check"]))
        except (ValueError, KeyError, TypeError):
            pass  # A damaged schedule should not prevent the next check.
    if time.time() < BOT_LEVEL_SYNC["next_check"]:
        return
    # Serialize config writes/reloads with dashboard operations, including shutdown.
    with LOCK:
        if STATE["job"] and STATE["job"]["status"] == "running":
            return
        BOT_LEVEL_SYNC["next_check"] = time.time() + 300  # Back off after a failed check.
        row = sql("SELECT c.name,c.level,c.online FROM acore_characters.characters c "
                  "LEFT JOIN acore_playerbots.playerbots_account_type t ON t.account_id=c.account "
                  f"WHERE c.guid={int(guid)} AND COALESCE(t.account_type,0)=0;").split("\t")
        if len(row) != 3 or not re.fullmatch(r"[A-Za-z]{2,12}", row[0]):
            raise ValueError("Bot level source is missing or is not an eligible human character.")
        name, saved_level, online = row
        level = console(f"pinfo {name}").strip() if online == "1" else saved_level
        if not level.isdecimal() or not 1 <= int(level) <= 80:
            raise ValueError("Invalid human character level; bot configuration was not changed.")
        marker = (guid, level, READY_BOOT)
        changed = BOT_LEVEL_SYNC["applied"] != marker or values.get("BOT_LEVEL_MATCH_TARGET") != level
        if changed:
            save_settings({"BOT_LEVEL_MATCH_TARGET": level})
            ps_script("apply-config.ps1")
            # This reloads bracket bounds without rebuilding Playerbots' accounts/caches.
            output = console("reload config")
            if "Level management config reloaded." not in output:
                raise RuntimeError("Bot level reload was not confirmed; will retry in five minutes.")
        BOT_LEVEL_SYNC["applied"] = marker
        BOT_LEVEL_SYNC["next_check"] = time.time() + 86400
        schedule_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = schedule_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"guid": guid, "level": level,
                                        "next_check": BOT_LEVEL_SYNC["next_check"]}), encoding="utf-8")
        os.replace(temporary, schedule_path)
    if changed:
        event(f"Random bot range now follows {name}: levels 1–{min(80, int(level) + 10)}; next check in 24 hours (protected bots excluded).")


def monitor():
    global CACHE
    while True:
        try:
            CACHE = collect()
            try:
                sync_bot_level(CACHE)
            except Exception as exc:
                CACHE.setdefault("errors", []).append(f"Bot level sync: {exc}")
        except Exception as exc:
            CACHE = {"sampled_at": time.time(), "errors": [str(exc)]}
        time.sleep(5)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, status, data, kind="application/json"):
        content = json.dumps(data).encode() if kind == "application/json" else data
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def allowed(self):
        host = self.headers.get("Host", "")
        if host not in ("127.0.0.1:8765", "localhost:8765", "host.docker.internal:8765"):
            return False
        origin = self.headers.get("Origin")
        return not origin or origin == "http://" + host

    def do_GET(self):
        if not self.allowed():
            return self.send(403, {"error": "Local origin required"})
        if self.path == "/api/session":
            return self.send(200, {"token": TOKEN})
        if self.path == "/api/status":
            values = env_values()
            with LOCK:
                data = {**CACHE, **STATE, "settings": {key: values.get(key, default) for key, default in DEFAULTS.items()}}
                data["bot_levels"] = {key: values.get(key, default) for key, default in BOT_LEVEL_DEFAULTS.items()}
                data["bot_level_source"] = values.get("BOT_LEVEL_MATCH_TARGET", "13")
            return self.send(200, data)
        if self.path.startswith("/api/logs/"):
            try:
                return self.send(200, {"text": logs(self.path.removeprefix("/api/logs/"))})
            except Exception as exc:
                return self.send(400, {"error": str(exc)})
        files = {"/": ("control.html", "text/html; charset=utf-8"),
                 "/control.js": ("control.js", "text/javascript; charset=utf-8"),
                 "/control.css": ("control.css", "text/css; charset=utf-8")}
        if self.path in files:
            name, kind = files[self.path]
            return self.send(200, (ROOT / "dashboard/public" / name).read_bytes(), kind)
        self.send(404, {"error": "Not found"})

    def do_POST(self):
        if not self.allowed() or not secrets.compare_digest(self.headers.get("X-Control-Token", ""), TOKEN):
            return self.send(403, {"error": "Invalid control token or origin. Refresh this page."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                raise ValueError("Invalid request length")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or self.path != "/api/action":
                raise ValueError("Invalid request")
            submit(body.get("action"), body)
            self.send(202, {"accepted": True})
        except ValueError as exc:
            self.send(400, {"error": str(exc)})
        except RuntimeError as exc:
            self.send(409, {"error": str(exc)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=sorted(ACTIONS))
    parser.add_argument("--countdown", type=int, default=60)
    args = parser.parse_args()
    if args.action:
        with urllib.request.urlopen("http://127.0.0.1:8765/api/session") as response:
            token = json.load(response)["token"]
        request = urllib.request.Request("http://127.0.0.1:8765/api/action",
                  data=json.dumps({"action": args.action, "countdown": args.countdown}).encode(),
                  headers={"Content-Type": "application/json", "X-Control-Token": token})
        with urllib.request.urlopen(request) as response:
            print(response.read().decode())
        print("Watch progress: http://127.0.0.1:8765")
    else:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
        threading.Thread(target=monitor, daemon=True).start()
        server.serve_forever()
