#!/usr/bin/env python3
"""设计稿 → 前端规格提取（redline，还原度方案「规格提取层」A②）。

把 ④ 的设计稿 PNG 逆向成「前端可直接消费的精确样式规格」，让 ⑥ 从"看图猜"变"照规格做"，
消掉"设计（位图）↔ 实现（代码）不同源、中间隔着 agent 肉眼"这层信息损失。

**精度分工铁律**：能程序量的（颜色、尺寸）就程序量、并 snap 到 design-spec token；
只有语义（元素角色、icon 是什么、对齐意图）才交给 VLM(agent)。别让 agent 猜 hex/px。

本文件（第一步）只做最高确定性的两件——其余留给 ⑥ 手册指导 agent 填：
  1. **designWidth 基准**：相同尺寸对比的坐标系（1440/375…）。设计稿是 AI 生图，
     原生像素（如 1536×1024）≠ designWidth，需等比缩放解读；取色不受缩放影响。
  2. **色板取色 → snap 到最近 color token**：逐像素直接吸附到设计系统的离散档位再按覆盖率聚合
     （不量化，避免"纯白被量化偏移成浅灰"这类系统误差）。既压掉生图噪声（东 31 西 33 都归 32）、
     又保证 ⑥ 用的一定是设计系统合法值；每档的 avgDist 顺带量化"设计色离系统档多远"。

留给 agent(VLM) 的语义活（本脚本只出占位）：icon 语义→lucide 映射、字号/间距聚类定档。

Pillow 可选：缺失则跳过取色（降级——agent 手工逐个 hex 比对 snap），与 fidelity_diff 一致。
可独立 CLI，或被 pf_state.py / server.py import 调用。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import token_compile  # 复用 _flatten/_resolve，拿 spec.tokens 里 color token 的终值（含 alias 解析）


def _pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_tokens(spec):
    """从 design-spec 解析出所有 color token 的终值 → [(path, hex, (r,g,b))]。

    用 token_compile 解析 alias（semantic → primitive），只收终值是 #hex 的。"""
    resolved = token_compile._resolve(token_compile._flatten(spec.get("tokens", {})))
    out = []
    for path, entry in resolved.items():
        v = entry.get("value", "")
        is_color = entry.get("type") == "color" or path.startswith("color.")
        if is_color and isinstance(v, str) and v.startswith("#"):
            try:
                out.append((path, v, _hex_to_rgb(v)))
            except ValueError:
                pass
    return out


def snap_color(rgb, palette):
    """把测得 rgb snap 到最近的 color token（RGB 欧氏距离；进阶可换 CIEDE2000）。

    返回 {"token","value","dist"} 或 None（palette 空）。dist 越大＝设计色离系统档越远，
    是"要不要给设计系统补一个品牌色"的信号。"""
    if not palette:
        return None
    def d2(p):
        return sum((a - b) ** 2 for a, b in zip(rgb, p[2]))
    best = min(palette, key=d2)
    return {"token": best[0], "value": best[1], "dist": round(d2(best) ** 0.5, 1)}


def snap_histogram(Image, png_path, palette, max_w=240):
    """逐像素 snap 到最近 color token，再按覆盖率聚合。

    比"量化分桶取主色"准：不产生量化偏移（纯白 #fefefe 直接 snap 到 white，而非被量化到浅灰再 snap 错）。
    返回 ((W,H), [{token,value,coverage,avgMeasured,avgDist}…] 按覆盖降序)——
    coverage ≈ 该设计系统色在画面里占的面积；avgDist ≈ 该档实测与系统值的平均偏差。"""
    img = Image.open(png_path).convert("RGB")
    W, H = img.size
    sw = min(W, max_w)  # 缩到 ≤max_w 宽控制像素量（取色是统计，无需全分辨率）
    small = img.resize((sw, max(1, round(H * sw / W))))
    data = small.tobytes()
    n = max(1, len(data) // 3)
    acc = {}  # token → [count, Σr, Σg, Σb, Σdist, value]
    for i in range(0, len(data), 3):
        rgb = (data[i], data[i + 1], data[i + 2])
        s = snap_color(rgb, palette)
        if s is None:
            continue
        a = acc.get(s["token"])
        if a is None:
            a = acc[s["token"]] = [0, 0, 0, 0, 0.0, s["value"]]
        a[0] += 1
        a[1] += rgb[0]; a[2] += rgb[1]; a[3] += rgb[2]
        a[4] += s["dist"]
    rows = []
    for tok, (c, sr, sg, sb, sd, val) in acc.items():
        rows.append({"token": tok, "value": val, "coverage": round(c / n, 4),
                     "avgMeasured": "#%02x%02x%02x" % (round(sr / c), round(sg / c), round(sb / c)),
                     "avgDist": round(sd / c, 1)})
    rows.sort(key=lambda r: -r["coverage"])
    return (W, H), rows


def extract(png_path, spec, design_width, top=8):
    """核心：designWidth + 取色 snap。返回规格 dict。缺 Pillow → 只有骨架 + 降级提示。"""
    palette = color_tokens(spec)
    result = {
        "page": None,
        "designWidth": design_width,
        "palette": [],
        # 以下两项是 VLM(agent) 的语义活，脚本只出占位、由 ⑥ 手册指导 agent 填：
        "icons": {"_note": "语义映射由 agent 填：设计图每个 icon → lucide 组件名（同位替换，见 phase-6）"},
        "typeScale": {"_note": "字号/行高从位图反推最弱：agent 目测 snap 到 font.size.* / lineHeight.*；"
                               "缺合适档位（如超大标题 display）→ 回 phase-4 按语义补档，别硬 snap 到偏小档"},
    }
    Image = _pil()
    if Image is None:
        result["_warn"] = "缺 Pillow：跳过程序取色（降级——agent 手工逐个 hex 比对 snap）。pip install pillow 后可自动化"
        return result
    if not palette:
        result["_warn"] = "design-spec 无 color token：无法 snap，请先在 ②③④ 建色板 token"
        return result
    (W, H), rows = snap_histogram(Image, png_path, palette)
    result["nativePx"] = "%dx%d" % (W, H)
    result["note"] = "nativePx 是生图原生尺寸；等比缩放到 designWidth 解读，取色不受缩放影响"
    result["palette"] = rows[:top]
    return result


def main(argv):
    p = argparse.ArgumentParser(prog="redline", description="设计稿 → 前端规格提取（取色 snap + designWidth）")
    p.add_argument("--design", required=True, help="④ 设计稿 PNG")
    p.add_argument("--spec", required=True, help="design-spec.json（读 tokens 做 color snap）")
    p.add_argument("--width", type=int, required=True, help="designWidth 基准（如 1440 / 375）")
    p.add_argument("--top", type=int, default=8, help="取覆盖率前 N 档色（默认 8）")
    p.add_argument("--out", help="规格 JSON 输出路径（缺省打印到 stdout）")
    args = p.parse_args(argv)
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    result = extract(args.design, spec, args.width, top=args.top)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("✅ 规格提取 → %s" % args.out)
        if result.get("_warn"):
            print("⚠️ " + result["_warn"])
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
