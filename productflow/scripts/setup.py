#!/usr/bin/env python3
"""ProductFlow setup / doctor —— 装好之后跑一次，自检环境 + 跑测试，确认 ProductFlow 真的装对了、能正常工作。

什么时候跑：
- 朋友/新机器第一次装好 ProductFlow 后，跑 `python3 scripts/setup.py` 一次；
- Agent 首次进入 ProductFlow 流程时，也用它确认自己的运行环境就绪（"检查自己的工作效果"）。

它做两件事：① 逐项检查依赖（哪些必需、哪些缺了只是降级）；② 跑一遍 ProductFlow 自己的测试套件，
确认核心代码工作正常。最后给一个清楚的就绪/待办汇总 + 下一步启动命令。
"""
import glob
import importlib.util
import os
import shutil
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OK, WARN, BAD = "✅", "⚠️", "❌"
issues, warns = [], []   # issues=致命（挡核心流程）；warns=可选（缺了只降级）


def check(label, ok, detail="", fatal=True):
    print(f"{OK if ok else (BAD if fatal else WARN)} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        (issues if fatal else warns).append(label)
    return ok


def main():
    print("ProductFlow 自检（setup / doctor）\n" + "-" * 50)

    # 1. Python（必需）
    check(f"Python {sys.version.split()[0]}", sys.version_info >= (3, 8), "需要 ≥ 3.8")

    # 2. 前端 vendored 库（必需——操作台离线渲染要用）
    vendor = os.path.join(SKILL_DIR, "assets", "vendor")
    need = ["d3.min.js", "markmap-lib.js", "markmap-view.js", "viewer.min.js", "viewer.min.css"]
    missing = [f for f in need if not os.path.isfile(os.path.join(vendor, f))]
    check("前端依赖库 assets/vendor", not missing, f"缺 {missing}" if missing else "齐全")

    # 3. Python Playwright + chromium（找参考/截图/E2E 用；缺只影响这些步骤）
    pw = importlib.util.find_spec("playwright") is not None
    check("Python Playwright", pw, "缺则 ②找参考/⑥截图E2E 受限：pip install playwright" if not pw else "已装", fatal=False)
    if pw:
        caches = ["~/Library/Caches/ms-playwright", "~/.cache/ms-playwright"]
        chromium = any(glob.glob(os.path.expanduser(c) + "/chromium*") for c in caches)
        check("Playwright chromium", chromium, "playwright install chromium" if not chromium else "已装", fatal=False)

    # 4. Docker（⑦部署本地 Docker 用；缺只影响部署阶段）
    docker = shutil.which("docker")
    running = bool(docker) and subprocess.run(["docker", "info"], capture_output=True).returncode == 0
    check("Docker（⑦本地部署）", running,
          ("daemon 未启动" if docker and not running else ("未装：⑦可改用其它部署方式" if not docker else "可用")),
          fatal=False)

    # 5. OpenAI 生图 key（③首图/④页面 AI 生图用；缺则降级为手写代码版设计，仍可走完流程）
    key = os.path.isfile(os.path.expanduser("~/.config/openai/env"))
    check("OpenAI 生图 key ~/.config/openai/env", key,
          "缺则 ③首图/④页面 生图降级为手写代码（流程仍走得通）" if not key else "已配置", fatal=False)

    # 6. 跑 ProductFlow 自己的测试套件——确认核心代码工作正常（这就是"自检工作效果"）
    print("\n— 跑 ProductFlow 测试套件确认核心功能正常（约 20s）…")
    run = os.path.join(SKILL_DIR, "tests", "run.sh")
    if os.path.isfile(run):
        r = subprocess.run(["sh", run], capture_output=True, text=True)
        out = (r.stdout or "") + (r.stderr or "")
        ran = next((l for l in out.splitlines() if l.startswith("Ran ")), "")
        check("测试套件 tests/run.sh", r.returncode == 0 and "PASS" in out, ran or "见输出")
        if r.returncode != 0:
            print("   测试输出尾部：\n   " + "\n   ".join(out.strip().splitlines()[-6:]))
    else:
        check("测试套件 tests/run.sh", False, "缺失", fatal=False)

    # 汇总 + 下一步
    print("\n" + "=" * 50)
    if issues:
        print(f"{BAD} 有 {len(issues)} 个必须先解决的问题：{', '.join(issues)}")
        return 1
    if warns:
        print(f"{OK} 核心就绪。{len(warns)} 个可选项缺失（相关阶段会降级，不挡主流程）：{', '.join(warns)}")
    else:
        print(f"{OK} 全部就绪！")
    print(f"\n下一步 → 启动操作台：sh {os.path.join('scripts', 'start.sh')}")
    print("然后浏览器访问 http://127.0.0.1:7717/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
