import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error

spec = importlib.util.spec_from_file_location("control", Path(__file__).parents[1] / "control_server.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class SettingsTests(unittest.TestCase):
    def test_bounds_and_unknown_settings(self):
        for changes in ({"BOT_MIN": "-1"}, {"BOT_MAX": "1.5"}, {"XP_RATE_KILL": "nan"},
                        {"XP_RATE_KILL": "3;whoami"}, {"OLLAMA_CHAT_ENABLE": "2"}, {"BOT_MAX": "499"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                c.validate_settings({**c.DEFAULTS, **changes})
        with self.assertRaises(ValueError):
            c.validate_settings({**c.DEFAULTS, "DOCKER_DB_ROOT_PASSWORD": "bad"})

    def test_atomic_save_preserves_unrelated_values(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(c, "ROOT", Path(directory)):
            path = Path(directory) / ".env"
            path.write_text("# keep\nDOCKER_DB_ROOT_PASSWORD=secret\nXP_RATE_KILL=1\nXP_RATE_KILL=2\n")
            c.save_settings(c.validate_settings(c.DEFAULTS))
            content = path.read_text()
            self.assertIn("DOCKER_DB_ROOT_PASSWORD=secret", content)
            self.assertIn("# keep", content)
            self.assertEqual(content.count("XP_RATE_KILL="), 1)
            self.assertEqual(c.env_values()["XP_RATE_KILL"], "3")

    def test_invalid_actions_and_countdowns(self):
        for action in ("shell", [], None):
            with self.assertRaises(ValueError):
                c.submit(action, {})
        for countdown in (0, 301, True, "60"):
            with self.assertRaises(ValueError):
                c.submit("stop_world", {"countdown": countdown})

    def test_operations_are_serialized(self):
        with patch.dict(c.STATE, {"job": {"status": "running"}}):
            with self.assertRaises(RuntimeError):
                c.submit("reload_chat", {})

    def test_reload_does_not_run_when_world_stopped(self):
        with patch.object(c, "inspect_world", return_value=None), patch.object(c, "console") as console:
            with self.assertRaises(RuntimeError):
                c.perform("reload_chat", {})
            console.assert_not_called()

    def test_shutdown_warns_before_stop(self):
        calls = []
        with patch.object(c, "countdown", side_effect=lambda s: calls.append(("warn", s))), \
             patch.object(c, "stage"), patch.object(c, "compose", side_effect=lambda *a, **k: calls.append(a)):
            c.perform("stop_world", {"countdown": 60})
        self.assertEqual(calls[0], ("warn", 60))
        self.assertEqual(calls[1], ("stop", "-t", "120", "ac-worldserver"))

    def test_ready_requires_initialization_from_current_boot(self):
        services = json.dumps([{"Service": "ac-worldserver", "State": "running"},
                               {"Service": "ac-database", "State": "running"}])
        def fake_compose(*args, **kwargs):
            return services if args[0] == "ps" else "Still loading world data"
        with patch.object(c, "READY_BOOT", "old-boot"), patch.object(c, "compose", side_effect=fake_compose), \
             patch.object(c, "inspect_world", return_value={"State": {"StartedAt": "new-boot"}}), \
             patch.object(c, "logs", return_value=""), patch.object(c, "sql", side_effect=["127.0.0.1\t0", "0\t0"]), \
             patch.object(c, "env_values", return_value={}), patch.object(c.socket, "create_connection"), \
             patch.object(c, "ollama", return_value={"models": []}), patch.object(c, "ps_script", return_value="0"):
            self.assertEqual(c.collect()["realm"], "starting")


class BotRangeControlsTests(unittest.TestCase):
    def test_rejects_bad_ranges_and_unexpected_keys(self):
        for change in ({"BOT_LEVEL_MIN": "0"}, {"BOT_LEVEL_MAX": "81"},
                       {"BOT_LEVEL_MIN": "25"}, {"BOT_LEVEL_MAX": "2.5"},
                       {"BOT_LEVEL_MODE": "shell"}, {"extra": "1"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                c.validate_bot_levels({**c.BOT_LEVEL_DEFAULTS, **change})
        self.assertEqual(c.validate_bot_levels({"BOT_LEVEL_MODE": "manual", "BOT_LEVEL_MIN": "80",
                                               "BOT_LEVEL_MAX": "80"})["BOT_LEVEL_MAX"], "80")

    def test_live_actions_only_reload_config_and_preserve_selected_mode(self):
        for action, spread in (("apply_bot_levels", "0"), ("spread_bot_levels", "1")):
            with self.subTest(action=action), patch.object(c, "inspect_world", return_value={"State": {"Running": True}}), \
                 patch.object(c, "save_settings") as save, patch.object(c, "ps_script"), patch.object(c, "stage"), \
                 patch.object(c, "console", return_value="Level management config reloaded.") as console, \
                 patch.object(c, "compose") as compose:
                c.perform(action, {"settings": {**c.BOT_LEVEL_DEFAULTS, "BOT_LEVEL_MODE": "manual"}})
                self.assertEqual(save.call_args.args[0]["BOT_LEVEL_SPREAD"], spread)
                self.assertEqual(save.call_args.args[0]["BOT_LEVEL_MODE"], "manual")
                console.assert_called_once_with("reload config")
                compose.assert_not_called()

    def test_stopped_world_rejects_live_action_without_saving(self):
        with patch.object(c, "inspect_world", return_value=None), patch.object(c, "save_settings") as save:
            with self.assertRaises(RuntimeError):
                c.perform("apply_bot_levels", {"settings": c.BOT_LEVEL_DEFAULTS})
            save.assert_not_called()

    def test_save_only_does_not_touch_running_world(self):
        with patch.object(c, "save_settings"), patch.object(c, "ps_script"), \
             patch.object(c, "console") as console, patch.object(c, "compose") as compose:
            c.perform("save_bot_levels", {"settings": {**c.BOT_LEVEL_DEFAULTS, "BOT_LEVEL_MODE": "manual"}})
            console.assert_not_called()
            compose.assert_not_called()


class BotLevelSyncTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(c, "ROOT", Path(directory)))
        self.values = {"BOT_LEVEL_MATCH_ENABLE": "1", "BOT_LEVEL_MATCH_GUID": "1001",
                       "BOT_LEVEL_MATCH_TARGET": "13"}
        self.enterContext(patch.object(c, "env_values", return_value=self.values))
        self.enterContext(patch.dict(c.BOT_LEVEL_SYNC, {"next_check": 0, "applied": None}))
        self.enterContext(patch.dict(c.STATE, {"job": None}))
        self.enterContext(patch.object(c, "READY_BOOT", "boot-1"))
        self.query = self.enterContext(patch.object(c, "sql", return_value="Magic\t13\t1"))
        self.console = self.enterContext(patch.object(c, "console", side_effect=self.reply))
        self.save = self.enterContext(patch.object(c, "save_settings", side_effect=self.values.update))
        self.generate = self.enterContext(patch.object(c, "ps_script"))
        self.enterContext(patch.object(c, "event"))

    @staticmethod
    def reply(command):
        return "14\n" if command == "pinfo Magic" else "[RandomBotLevelMgr] Level management config reloaded."

    def test_live_level_overrides_stale_save_and_unchanged_level_does_not_reload(self):
        c.sync_bot_level({"realm": "ready"})
        self.save.assert_called_once_with({"BOT_LEVEL_MATCH_TARGET": "14"})
        self.assertEqual([call.args[0] for call in self.console.call_args_list], ["pinfo Magic", "reload config"])
        c.sync_bot_level({"realm": "ready"})  # poll is throttled
        self.assertEqual(self.query.call_count, 1)
        c.BOT_LEVEL_SYNC["next_check"] = 0
        c.sync_bot_level({"realm": "ready"})
        self.assertEqual(self.generate.call_count, 1)

    def test_offline_character_uses_saved_level(self):
        self.query.return_value = "Magic\t15\t0"
        c.sync_bot_level({"realm": "ready"})
        self.save.assert_called_once_with({"BOT_LEVEL_MATCH_TARGET": "15"})
        self.console.assert_called_once_with("reload config")

    def test_daily_schedule_survives_controller_restart(self):
        with patch.object(c.time, "time", return_value=1000000):
            c.sync_bot_level({"realm": "ready"})
        self.assertEqual(c.BOT_LEVEL_SYNC["next_check"], 1086400)
        c.BOT_LEVEL_SYNC.update(next_check=0, applied=None)
        with patch.object(c.time, "time", return_value=1086399):
            c.sync_bot_level({"realm": "ready"})
        self.assertEqual(self.query.call_count, 1)
        with patch.object(c.time, "time", return_value=1086400):
            c.sync_bot_level({"realm": "ready"})
        self.assertEqual(self.query.call_count, 2)

    def test_busy_stopped_and_disabled_do_not_change_anything(self):
        c.sync_bot_level({"realm": "offline"})
        self.values["BOT_LEVEL_MODE"] = "manual"
        c.sync_bot_level({"realm": "ready"})
        self.values["BOT_LEVEL_MODE"] = "follow"
        with patch.dict(c.STATE, {"job": {"status": "running"}}):
            c.sync_bot_level({"realm": "ready"})
        self.values["BOT_LEVEL_MATCH_GUID"] = "0"
        c.sync_bot_level({"realm": "ready"})
        self.query.assert_not_called()
        self.save.assert_not_called()

    def test_invalid_or_missing_source_cannot_mutate_config(self):
        for row in ("", "Magic\t0\t0", "Magic\t81\t0", "Magic;shutdown\t13\t1"):
            c.BOT_LEVEL_SYNC["next_check"] = 0
            self.query.return_value = row
            with self.subTest(row=row), self.assertRaises(ValueError):
                c.sync_bot_level({"realm": "ready"})
        self.save.assert_not_called()

    def test_failed_reload_is_retried_even_after_target_was_saved(self):
        self.console.side_effect = lambda command: "14" if command.startswith("pinfo") else ""
        with self.assertRaises(RuntimeError):
            c.sync_bot_level({"realm": "ready"})
        self.assertIsNone(c.BOT_LEVEL_SYNC["applied"])
        c.BOT_LEVEL_SYNC["next_check"] = 0
        self.console.side_effect = self.reply
        c.sync_bot_level({"realm": "ready"})
        self.assertEqual(c.BOT_LEVEL_SYNC["applied"], ("1001", "14", "boot-1"))


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = c.http.server.ThreadingHTTPServer(("127.0.0.1", 0), c.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, body=None, **headers):
        request = urllib.request.Request(self.url + path, data=body,
                    headers={"Host": "127.0.0.1:8765", **headers})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code

    def test_csrf_and_host_protection(self):
        body = json.dumps({"action": "stop_all"}).encode()
        self.assertEqual(self.request("/api/action", body), 403)
        self.assertEqual(self.request("/api/action", body, **{"X-Control-Token": c.TOKEN, "Origin": "https://evil.example"}), 403)
        self.assertEqual(self.request("/api/session", Host="evil.example"), 403)
        self.assertEqual(self.request("/api/session"), 200)

    def test_unknown_action_does_not_spawn(self):
        with patch.object(c, "perform") as perform:
            self.assertEqual(self.request("/api/action", b'{"action":"shell"}', **{"X-Control-Token": c.TOKEN}), 400)
            perform.assert_not_called()


if __name__ == "__main__":
    unittest.main()
