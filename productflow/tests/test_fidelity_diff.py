"""fidelity_diff.py 单元测。improved/severity_score 是纯逻辑（无依赖）；diff 需 Pillow（无则 skip）。"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import fidelity_diff as fd  # noqa: E402  顶部无 Pillow 依赖（Pillow 延迟到函数内）

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ImprovedGuardTest(unittest.TestCase):
    """自纠护栏(b)「只接受确有改进」纯逻辑（专题 C5）。"""

    def test_severity_score(self):
        self.assertEqual(fd.severity_score([{"severity": "minor"}, {"severity": "major"}]), 4)
        self.assertEqual(fd.severity_score([]), 0)
        self.assertEqual(fd.severity_score([{"severity": "blocker"}]), 9)

    def test_improved_when_severity_down(self):
        self.assertTrue(fd.improved([{"severity": "blocker"}], [{"severity": "minor"}]))

    def test_not_improved_when_same(self):
        self.assertFalse(fd.improved([{"severity": "major"}], [{"severity": "major"}]))

    def test_improved_when_fewer_at_same_severity(self):
        self.assertTrue(fd.improved([{"severity": "minor"}, {"severity": "minor"}], [{"severity": "minor"}]))

    def test_not_improved_when_worse(self):
        self.assertFalse(fd.improved([{"severity": "minor"}], [{"severity": "blocker"}]))


@unittest.skipUnless(HAS_PIL, "需要 Pillow")
class FidelityDiffTest(unittest.TestCase):
    def _pair(self, d):
        a, b = os.path.join(d, "a.png"), os.path.join(d, "b.png")
        ia = Image.new("RGB", (20, 20), (52, 152, 219))
        ia.save(a)
        ib = ia.copy()
        for x in range(10):
            for y in range(10):
                ib.putpixel((x, y), (255, 0, 0))
        ib.save(b)
        return a, b

    def test_diff_ratio_and_output(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = self._pair(d)
            out = os.path.join(d, "diff.png")
            r = fd.diff(a, b, out)
            self.assertIsNotNone(r)
            self.assertTrue(os.path.isfile(out))
            self.assertAlmostEqual(r["diff_ratio"], 0.25, delta=0.05)

    def test_align_handles_different_sizes(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.png"), os.path.join(d, "b.png")
            Image.new("RGB", (40, 40), (0, 0, 0)).save(a)
            Image.new("RGB", (20, 20), (0, 0, 0)).save(b)
            out = os.path.join(d, "diff.png")
            r = fd.diff(a, b, out)
            self.assertIsNotNone(r)
            self.assertTrue(os.path.isfile(out))


if __name__ == "__main__":
    unittest.main()
