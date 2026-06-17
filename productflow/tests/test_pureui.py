"""Unit tests for the Phase 3/4 pure-UI generation helpers in server.py.

These guard the "direct platform UI, no scene/background" behavior so it can't be
silently regressed: the platform→size mapping, primary reading, and the pure-UI
rule block (which must steer away from the style-polluting --subject/--category mode).
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import server as S  # noqa: E402


class PlatformSpec(unittest.TestCase):
    def test_size_per_platform(self):
        self.assertEqual(S._platform_ui_spec("APP")[2], "1080x2340")  # phone portrait
        self.assertEqual(S._platform_ui_spec("H5")[2], "1080x2340")   # mobile web portrait
        self.assertEqual(S._platform_ui_spec("PC")[2], "1440x1080")   # desktop landscape

    def test_case_insensitive(self):
        self.assertEqual(S._platform_ui_spec("app")[2], "1080x2340")

    def test_unknown_falls_back_to_pc(self):
        self.assertEqual(S._platform_ui_spec("XYZ")[2], "1440x1080")
        self.assertEqual(S._platform_ui_spec("")[2], "1440x1080")

    def test_desc_describes_pure_ui_not_device(self):
        # APP description must frame the status bar as UI, not a physical device frame
        name, desc, _ = S._platform_ui_spec("APP")
        self.assertIn("App", name)
        self.assertIn("不是设备", desc)


class ReadPrimary(unittest.TestCase):
    def _wizard(self, pf, obj):
        with open(os.path.join(pf, "wizard.json"), "w", encoding="utf-8") as f:
            json.dump(obj, f)

    def test_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as pf:
            self.assertIsNone(S._read_primary(pf))

    def test_reads_and_uppercases(self):
        with tempfile.TemporaryDirectory() as pf:
            self._wizard(pf, {"primary": "app"})
            self.assertEqual(S._read_primary(pf), "APP")

    def test_invalid_primary_returns_none(self):
        with tempfile.TemporaryDirectory() as pf:
            self._wizard(pf, {"primary": "watch"})
            self.assertIsNone(S._read_primary(pf))


class PureUiRules(unittest.TestCase):
    def test_rules_mandate_prompt_mode_and_forbid_subject_category(self):
        r = S._PURE_UI_RULES
        # must steer to --prompt and explicitly warn off the style-polluting path
        self.assertIn("--prompt", r)
        self.assertIn("--subject", r)
        self.assertIn("--category web-design", r)
        # core bans present
        for ban in ("背景", "场景", "设备外框", "edge-to-edge"):
            self.assertIn(ban, r)


if __name__ == "__main__":
    unittest.main()
