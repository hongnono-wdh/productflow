"""Unit tests for explore request-slot clearing (server._clear_explore_slot).

Guards the "③ 生成首图 status" behavior: a stuck/orphaned gen-heroes slot must clear
AND set heroGenFailed (so the console can show "上次生成未完成，可重试" instead of an
unexplained empty canvas). The startup sweep relies on the kind=None (clear-all) path.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import server as S  # noqa: E402


class ClearExploreSlot(unittest.TestCase):
    def test_gen_heroes_clears_and_marks_failed(self):
        ex = {"request": {"gen-heroes": {"kind": "gen-heroes"}}}
        self.assertTrue(S._clear_explore_slot(ex, "gen-heroes"))
        self.assertEqual(ex["request"], {})
        self.assertTrue(ex["heroGenFailed"])

    def test_search_refs_clears_without_hero_flag(self):
        ex = {"request": {"search-refs": {"kind": "search-refs"}}}
        self.assertTrue(S._clear_explore_slot(ex, "search-refs"))
        self.assertEqual(ex["request"], {})
        self.assertNotIn("heroGenFailed", ex)

    def test_clear_all_orphans_marks_failed_if_gen_heroes_present(self):
        ex = {"request": {"search-refs": {}, "gen-heroes": {}}}
        self.assertTrue(S._clear_explore_slot(ex, None))  # startup sweep path
        self.assertEqual(ex["request"], {})
        self.assertTrue(ex["heroGenFailed"])

    def test_noop_when_no_slots(self):
        self.assertFalse(S._clear_explore_slot({"request": {}}, None))
        self.assertFalse(S._clear_explore_slot({}, "gen-heroes"))


if __name__ == "__main__":
    unittest.main()
