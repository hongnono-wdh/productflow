"""token_compile.py 单元测试。纯函数、无 ~/.productflow 副作用 → 允许 in-process import。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import token_compile as tc  # noqa: E402


class TokenCompileTest(unittest.TestCase):
    TOKENS = {
        "color": {
            "blue": {"500": {"$value": "#3498db", "$type": "color"}},
            "action": {"primary": {"$value": "{color.blue.500}", "$type": "color"}},
        },
        "space": {"4": {"$value": "16px", "$type": "dimension"}},
        "lineHeight": {"normal": {"$value": "1.5", "$type": "number"}},
    }

    def _r(self):
        return tc._resolve(tc._flatten(self.TOKENS))

    def test_alias_resolved_to_terminal_value(self):
        self.assertEqual(self._r()["color.action.primary"]["value"], "#3498db")

    def test_css_output(self):
        css = tc.compile_css(self._r())
        self.assertIn("--color-action-primary: #3498db;", css)
        self.assertIn("--space-4: 16px;", css)

    def test_swift_output(self):
        sw = tc.compile_swift(self._r())
        self.assertIn('static let colorActionPrimary = Color(hex: "3498DB")', sw)
        self.assertIn("static let space4 = CGFloat(16)", sw)
        self.assertIn("init(hex: String)", sw)  # 附带 Color(hex:) 扩展

    def test_compose_output(self):
        kt = tc.compile_compose(self._r())
        self.assertIn("val ColorActionPrimary = Color(0xFF3498DB)", kt)
        self.assertIn("val Space4 = 16.dp", kt)

    def test_lineheight_stays_unitless(self):
        """补 line-height 维度：number 类型 → CSS 原值 1.5，不被当 dimension 编成 CGFloat/dp。"""
        r = self._r()
        self.assertIn("--lineHeight-normal: 1.5;", tc.compile_css(r))
        sw = tc.compile_swift(r)
        self.assertIn('static let lineHeightNormal = "1.5"', sw)
        self.assertNotIn("CGFloat(1.5)", sw)          # 关键：没被误当尺寸
        self.assertNotIn("1.5.dp", tc.compile_compose(r))

    def test_cycle_raises(self):
        cyc = {"a": {"$value": "{b}", "$type": "color"}, "b": {"$value": "{a}", "$type": "color"}}
        with self.assertRaises(ValueError):
            tc._resolve(tc._flatten(cyc))

    def test_dangling_alias_raises(self):
        d = {"a": {"$value": "{nope.x}", "$type": "color"}}
        with self.assertRaises(ValueError):
            tc._resolve(tc._flatten(d))

    def test_compile_spec_writes_three_ends(self):
        import tempfile
        spec = {"tokens": self.TOKENS}
        with tempfile.TemporaryDirectory() as d:
            written = tc.compile_spec(spec, "all", d)
            names = sorted(os.path.basename(w) for w in written)
            self.assertEqual(names, ["Tokens.kt", "Tokens.swift", "tokens.css"])


if __name__ == "__main__":
    unittest.main()
