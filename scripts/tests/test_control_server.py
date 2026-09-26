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
