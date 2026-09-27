import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("console", Path(__file__).parents[1] / "control_console.py")
console = importlib.util.module_from_spec(spec)
spec.loader.exec_module(console)


class PlayerLevelTests(unittest.TestCase):
    def test_only_character_level_is_returned(self):
        output = "Account: private\nSecurity Level: 3\n\x1b[36m| Level: 14 (200/1000 XP)\nIP: private"
        self.assertEqual(console.extract_player_level(output), "14")
        self.assertEqual(console.extract_player_level("| Level: 80\n"), "80")

    def test_missing_ambiguous_or_invalid_level_is_rejected(self):
        for output in ("Security Level: 3", "| Level: 81", "| Level: 0", "| Level: 13\n| Level: 14"):
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                console.extract_player_level(output)
