"""fidelity_diff.py 单元测（纯图像处理、无 ~/.productflow 副作用 → in-process import）。
缺 Pillow 时整体 skip（与流水线的图像依赖降级一致）。"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

try:
    from PIL import Image
    import fidelity_diff as fd
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@unittest.skipUnless(HAS_PIL, "需要 Pillow")
class FidelityDiffTest(unittest.TestCase):
    def _pair(self, d):
        a, b = os.path.join(d, "a.png"), os.path.join(d, "b.png")
        ia = Image.new("RGB", (20, 20), (52, 152, 219))
        ia.save(a)
        ib = ia.copy()
        for x in range(10):
            for y in range(10):
                ib.putpixel((x, y), (255, 0, 0))  # 改红 1/4 面积
        ib.save(b)
        return a, b

    def test_diff_ratio_and_output(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = self._pair(d)
            out = os.path.join(d, "diff.png")
            r = fd.diff(a, b, out)
            self.assertIsNotNone(r)
            self.assertTrue(os.path.isfile(out))
            self.assertAlmostEqual(r["diff_ratio"], 0.25, delta=0.05)  # 100/400

    def test_align_handles_different_sizes(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.png"), os.path.join(d, "b.png")
            Image.new("RGB", (40, 40), (0, 0, 0)).save(a)
            Image.new("RGB", (20, 20), (0, 0, 0)).save(b)  # 异尺寸
            out = os.path.join(d, "diff.png")
            r = fd.diff(a, b, out)  # 归一化对齐后不崩
            self.assertIsNotNone(r)
            self.assertTrue(os.path.isfile(out))


if __name__ == "__main__":
    unittest.main()
