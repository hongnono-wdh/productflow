#!/usr/bin/env python3
"""还原度差异图（软证据层，专题 C3）——薄封装，不自研 diff 算法。

- Pillow 做 IO + 归一化对齐（设计稿↔实现异源不可像素对齐，先缩放/pad 到同尺寸）；
- 优先用现成 `pixelmatch` PyPI 移植做像素 diff（忽略抗锯齿）；没装则退到 Pillow 朴素逐像素 diff。
- 产物：差异热力图 PNG + 差异比例数字。**仅作「给人和 LLM 裁判看的证据 + 疑似大偏差软告警」，
  绝不作 pass/fail 判据**（判定交给 LLM 视觉裁判 + DOM 断言，见专题 C）。
- Web/桌面场景亦可换用开源 uiMatch（Node，含 ΔE2000/DFS）——本脚本是跨平台的纯 Python 兜底。
- 缺 Pillow → 返回 None（优雅降级：只靠裁判 + 断言）。
"""
import argparse
import sys


def _pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


def align(Image, design, impl):
    """把两图等比缩放到同宽、再 pad 到同高（异源图对齐的最简做法）。"""
    w = max(design.width, impl.width)

    def fit(im):
        im = im.convert("RGBA")
        if im.width != w:
            im = im.resize((w, round(im.height * w / im.width)))
        return im

    d, i = fit(design), fit(impl)
    h = max(d.height, i.height)

    def pad(im):
        if im.height == h:
            return im
        bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))
        bg.paste(im, (0, 0))
        return bg

    return pad(d), pad(i), w, h


def diff(design_path, impl_path, out_path):
    """返回 {"diff_ratio": 0..1, "out": path, "engine": ...} 或 None（缺 Pillow 降级）。"""
    Image = _pil()
    if Image is None:
        return None
    d, i, w, h = align(Image, Image.open(design_path), Image.open(impl_path))
    total = w * h
    try:
        from pixelmatch import pixelmatch
        out = bytearray(total * 4)
        n = pixelmatch(list(d.tobytes()), list(i.tobytes()), w, h, out,
                       includeAA=False, threshold=0.1)
        Image.frombytes("RGBA", (w, h), bytes(out)).save(out_path)
        engine = "pixelmatch"
    except ImportError:
        # 无 pixelmatch：Pillow 朴素逐像素 diff（保守、够作软证据；标红明显不同的像素）
        out = Image.new("RGBA", (w, h))
        dp, ip, op = d.load(), i.load(), out.load()
        n = 0
        for y in range(h):
            for x in range(w):
                a, b = dp[x, y], ip[x, y]
                if abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) > 60:
                    op[x, y] = (255, 0, 0, 255)
                    n += 1
                else:
                    op[x, y] = (a[0], a[1], a[2], 40)
        out.save(out_path)
        engine = "pillow-naive"
    return {"diff_ratio": n / total if total else 0.0, "out": out_path, "engine": engine}


_SEV = {"minor": 1, "major": 3, "blocker": 9}


def severity_score(diffs):
    """差异清单严重度总分（minor=1 / major=3 / blocker=9）。"""
    return sum(_SEV.get((d or {}).get("severity", "minor"), 1) for d in (diffs or []))


def improved(prev_diffs, new_diffs):
    """自纠护栏(b)：新一轮相对上一轮是否「确有改进」——严重度总分下降，或同分但条数更少。
    未改进 → False（应回退上一版、停止自纠，专题 C5）。"""
    ps, ns = severity_score(prev_diffs), severity_score(new_diffs)
    if ns != ps:
        return ns < ps
    return len(new_diffs or []) < len(prev_diffs or [])


def main(argv):
    p = argparse.ArgumentParser(prog="fidelity_diff", description="设计稿↔实现 差异图（软证据，不 gate）")
    p.add_argument("--design", required=True, help="④ 设计稿图")
    p.add_argument("--impl", required=True, help="⑥ 实现截图")
    p.add_argument("--out", required=True, help="差异热力图输出路径")
    args = p.parse_args(argv)
    r = diff(args.design, args.impl, args.out)
    if r is None:
        print("⚠️ 缺 Pillow，跳过差异图（降级：只靠 LLM 裁判 + DOM 断言）")
        return 0
    print(f"✅ 差异图 {r['out']}（{r['engine']}）｜差异比例 {r['diff_ratio'] * 100:.1f}%"
          f"（软证据，不作 pass/fail）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
