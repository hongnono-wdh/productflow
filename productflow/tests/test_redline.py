"""redline.py 单元测。snap/hex/token 解析是纯逻辑（无依赖）；取色需 Pillow（无则 skip）。

与 test_fidelity_diff 同款：顶部无 Pillow 依赖（延迟到函数内），造纯色 PNG 验证取色 snap。"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import redline as rl  # noqa: E402

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class PureLogicTest(unittest.TestCase):
    """无 Pillow 也必须绿：hex 解析 / color token 解析（含 alias）/ snap 最近档。"""

    def test_hex_to_rgb(self):
        self.assertEqual(rl._hex_to_rgb("#2563eb"), (37, 99, 235))
        self.assertEqual(rl._hex_to_rgb("#fff"), (255, 255, 255))  # 短写扩展

    def test_color_tokens_resolves_alias(self):
        spec = {"tokens": {"color": {
            "blue": {"500": {"$value": "#2563eb", "$type": "color"}},
            "action": {"primary": {"$value": "{color.blue.500}", "$type": "color"}},
        }}}
        got = rl.color_tokens(spec)
        paths = {p for p, _h, _rgb in got}
        self.assertIn("color.blue.500", paths)
        self.assertIn("color.action.primary", paths)
        # semantic alias 被解析成 primitive 的终值 hex
        for path, hexv, rgb in got:
            self.assertEqual(hexv, "#2563eb")
            self.assertEqual(rgb, (37, 99, 235))

    def test_snap_color_picks_nearest(self):
        palette = [
            ("color.blue.500", "#2563eb", (37, 99, 235)),
            ("color.slate.900", "#0f172a", (15, 23, 42)),
            ("color.white", "#ffffff", (255, 255, 255)),
        ]
        # 设计稿里更亮的蓝 #1058f0 → 应 snap 到 blue.500，而非 slate/white
        snapped = rl.snap_color((16, 88, 240), palette)
        self.assertEqual(snapped["token"], "color.blue.500")
        self.assertEqual(snapped["value"], "#2563eb")
        self.assertGreater(snapped["dist"], 0)  # 有微差，dist 记录它

    def test_snap_empty_palette_returns_none(self):
        self.assertIsNone(rl.snap_color((1, 2, 3), []))

    def test_extract_has_designwidth_and_placeholders(self):
        spec = {"tokens": {"color": {"blue": {"500": {"$value": "#2563eb", "$type": "color"}}}}}
        with tempfile.TemporaryDirectory() as d:
            # 无论 Pillow 有无，designWidth 与语义占位必须在（缺 Pillow 走降级分支）
            png = os.path.join(d, "x.png")
            if HAS_PIL:
                Image.new("RGB", (8, 8), (37, 99, 235)).save(png)
            r = rl.extract(png if HAS_PIL else "/nonexistent", spec, 1440) if HAS_PIL \
                else rl.extract("/nonexistent", spec, 1440)
            self.assertEqual(r["designWidth"], 1440)
            self.assertIn("_note", r["icons"])
            self.assertIn("_note", r["typeScale"])


@unittest.skipUnless(HAS_PIL, "需要 Pillow")
class ColorSamplingTest(unittest.TestCase):
    def test_solid_png_snaps_to_matching_token(self):
        spec = {"tokens": {"color": {
            "blue": {"500": {"$value": "#2563eb", "$type": "color"}},
            "slate": {"900": {"$value": "#0f172a", "$type": "color"}},
            "white": {"$value": "#ffffff", "$type": "color"},
        }}}
        with tempfile.TemporaryDirectory() as d:
            png = os.path.join(d, "hero.png")
            Image.new("RGB", (40, 40), (37, 99, 235)).save(png)  # 纯 blue.500
            r = rl.extract(png, spec, 1440)
            self.assertEqual(r["nativePx"], "40x40")
            self.assertTrue(r["palette"], "应取到主色")
            top = r["palette"][0]
            self.assertEqual(top["value"], "#2563eb")  # 主色 snap 到 blue.500

    def test_scaled_generated_size_reported(self):
        spec = {"tokens": {"color": {"white": {"$value": "#ffffff", "$type": "color"}}}}
        with tempfile.TemporaryDirectory() as d:
            png = os.path.join(d, "g.png")
            Image.new("RGB", (1536, 1024), (255, 255, 255)).save(png)  # 生图原生尺寸
            r = rl.extract(png, spec, 1440)  # designWidth ≠ nativePx
            self.assertEqual(r["designWidth"], 1440)
            self.assertEqual(r["nativePx"], "1536x1024")


if __name__ == "__main__":
    unittest.main()
