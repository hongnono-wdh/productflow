#!/usr/bin/env python3
"""ProductFlow design-spec token 编译器：一份 tokens → Web(CSS) / iOS(Swift) / Android(Compose)。

纯标准库、零三方依赖（对比 Style Dictionary 的 Node 依赖：这个轮子极小，自研更划算、守「端上零依赖」铁律）。
可独立 CLI，或被 pf_state.py `spec compile` 调用。让「三端一致」成为编译产物而非 AI 自觉。
"""

import argparse
import json
import os
import re
import sys

_ALIAS = re.compile(r"\{([^}]+)\}")


def _flatten(tokens: dict) -> dict:
    """tokens 树 → {点分 path: {"value":.., "type":..}}。叶子 = 含 $value 的 dict。"""
    out: dict = {}

    def walk(node, prefix):
        if isinstance(node, dict) and "$value" in node:
            out[".".join(prefix)] = {"value": node["$value"], "type": node.get("$type", "")}
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, prefix + [k])

    walk(tokens or {}, [])
    return out


def _resolve(flat: dict) -> dict:
    """解析别名 {a.b.c} 到终值；悬空引用 / 成环 → ValueError。返回 {path: {value, type}}。"""
    resolved: dict = {}

    def rec(path, stack):
        if path in resolved:
            return resolved[path]
        if path not in flat:
            raise ValueError(f"悬空 alias：引用了不存在的 token「{path}」")
        if path in stack:
            raise ValueError("token alias 成环：" + " → ".join(stack + [path]))
        entry = flat[path]
        val, typ = entry["value"], entry["type"]
        m = _ALIAS.fullmatch(val.strip()) if isinstance(val, str) else None
        if m:
            target = rec(m.group(1), stack + [path])
            out = {"value": target["value"], "type": typ or target["type"]}
        else:
            out = {"value": val, "type": typ}
        resolved[path] = out
        return out

    for p in flat:
        rec(p, [])
    return resolved


# ── 命名转换 ──
def _kebab(path: str) -> str:
    return "--" + path.replace(".", "-")


def _camel(path: str) -> str:
    segs = re.split(r"[.\-]", path)
    return segs[0] + "".join(s[:1].upper() + s[1:] for s in segs[1:])


def _pascal(path: str) -> str:
    return "".join(s[:1].upper() + s[1:] for s in re.split(r"[.\-]", path))


# ── 值转换（按 $type）──
def _hex6(v: str) -> str:
    return v.lstrip("#").upper()


def _num(v) -> str:
    return re.sub(r"[a-zA-Z%]+$", "", str(v))


def _css_value(value, typ) -> str:
    return str(value)  # CSS 直接用原值（#hex / 16px / font / shadow）


def _swift_value(value, typ) -> str:
    if typ == "color":
        return f'Color(hex: "{_hex6(value)}")'
    if typ == "dimension":
        return f"CGFloat({_num(value)})"
    return f'"{value}"'  # fontFamily / shadow / 其它 → 字符串


def _compose_value(value, typ) -> str:
    if typ == "color":
        return f"Color(0xFF{_hex6(value)})"
    if typ == "dimension":
        return f"{_num(value)}.dp"
    return f'"{value}"'


# ── 三端输出 ──
def compile_css(resolved: dict) -> str:
    lines = [":root {"]
    for p in sorted(resolved):
        lines.append(f"  {_kebab(p)}: {_css_value(resolved[p]['value'], resolved[p]['type'])};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def compile_swift(resolved: dict) -> str:
    lines = ["import SwiftUI", "", "enum Tokens {"]
    for p in sorted(resolved):
        lines.append(f"    static let {_camel(p)} = {_swift_value(resolved[p]['value'], resolved[p]['type'])}")
    lines += [
        "}", "",
        "extension Color {",
        "    init(hex: String) {",
        "        var v: UInt64 = 0; Scanner(string: hex).scanHexInt64(&v)",
        "        self.init(.sRGB, red: Double((v >> 16) & 0xff) / 255,"
        " green: Double((v >> 8) & 0xff) / 255, blue: Double(v & 0xff) / 255, opacity: 1)",
        "    }",
        "}",
    ]
    return "\n".join(lines) + "\n"


def compile_compose(resolved: dict) -> str:
    lines = ["import androidx.compose.ui.graphics.Color", "import androidx.compose.ui.unit.dp", "", "object Tokens {"]
    for p in sorted(resolved):
        lines.append(f"    val {_pascal(p)} = {_compose_value(resolved[p]['value'], resolved[p]['type'])}")
    lines.append("}")
    return "\n".join(lines) + "\n"


_TARGETS = {
    "PC": [("tokens.css", compile_css)],
    "H5": [("tokens.css", compile_css)],
    "APP": [("Tokens.swift", compile_swift), ("Tokens.kt", compile_compose)],
}


def compile_spec(spec: dict, platform: str, out_dir: str) -> list:
    """按平台把 spec.tokens 编译到 out_dir，返回写出的文件路径列表。"""
    resolved = _resolve(_flatten(spec.get("tokens", {}) if isinstance(spec, dict) else {}))
    plats = ["PC", "H5", "APP"] if platform == "all" else [platform]
    os.makedirs(out_dir, exist_ok=True)
    written, seen = [], set()
    for pl in plats:
        for fname, fn in _TARGETS.get(pl, []):
            if fname in seen:
                continue  # PC/H5 共用 tokens.css，只写一次
            seen.add(fname)
            path = os.path.join(out_dir, fname)
            with open(path, "w", encoding="utf-8") as f:
                f.write(fn(resolved))
            written.append(path)
    return written


def main(argv: list) -> int:
    p = argparse.ArgumentParser(prog="token_compile", description="design-spec tokens → CSS/Swift/Compose")
    p.add_argument("--spec", required=True, help="design-spec.json 路径")
    p.add_argument("--platform", default="all", choices=["PC", "H5", "APP", "all"])
    p.add_argument("--out", required=True, help="输出目录")
    args = p.parse_args(argv)
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    for w in compile_spec(spec, args.platform, args.out):
        print(f"✅ {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
