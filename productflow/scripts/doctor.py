#!/usr/bin/env python3
"""ProductFlow doctor —— 安装后的「深度自检」，比 /productflow-init 更彻底。

在 setup.py（依赖检查 + 跑测试套件）基础上，额外做两件 setup 不做的事：
  ② 代码完整性：关键文件齐全且非空 + git 仓库完整性（确认装全了、没缺/没损坏）；
  ③ 真出图：实际调用本地 openai-image-gen 批量生成 2 张图，确认「生图通路 + 批量并发」都真的通
     （不是只看 key/skill 在不在，而是端到端真出一次）。

用法：
  python3 doctor.py              # 完整深度自检（含真调一次生图 API，约 2 张小图开销）
  python3 doctor.py --no-image   # 跳过真出图（不调用付费 API，例如 CI / 离线）
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

# realpath：即便经 ~/.claude/skills/productflow 软链调用，也定位到真实 clone（.git 所在）
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))   # .../productflow
REPO = os.path.dirname(SKILL_DIR)                                          # 仓库根（productflow 的上层）
OK, WARN, BAD = "✅", "⚠️", "❌"
issues, warns = [], []


def check(label, ok, detail="", fatal=True):
    print(f"{OK if ok else (BAD if fatal else WARN)} {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        (issues if fatal else warns).append(label)
    return ok


def run_setup_baseline() -> int:
    """复用 setup.py 跑「依赖 + 测试套件」基线（不重复造轮子）。"""
    setup = os.path.join(SKILL_DIR, "scripts", "setup.py")
    print("\n=== ① 依赖 + 测试套件（setup.py 基线）===")
    if not os.path.isfile(setup):
        check("setup.py 存在", False, "缺 scripts/setup.py")
        return 1
    return subprocess.run([sys.executable, setup]).returncode


def check_completeness():
    """② 代码完整性：关键文件 + 编译产物 + 7 阶段手册 + git 完整性。"""
    print("\n=== ② 代码完整性 ===")
    manifest = [
        "productflow/scripts/server.py", "productflow/scripts/pf_state.py",
        "productflow/scripts/setup.py", "productflow/scripts/start.sh",
        "productflow/SKILL.md", "productflow/VERSION",
        "productflow/assets/dist/index.html", "productflow/tests/run.sh",
        "openai-image-gen/scripts/gen.py", "openai-image-gen/scripts/edit.py",
        "openai-image-gen/SKILL.md",
    ]
    miss = [rel for rel in manifest
            if not (os.path.isfile(os.path.join(REPO, rel)) and os.path.getsize(os.path.join(REPO, rel)) > 0)]
    check("关键文件齐全且非空", not miss, f"缺/空: {miss}" if miss else f"{len(manifest)} 个关键文件 OK")

    js = glob.glob(os.path.join(SKILL_DIR, "assets", "dist", "assets", "*.js"))
    check("React 操作台编译产物 dist", bool(js),
          "缺 dist/assets/*.js —— cd web && npm run build" if not js else f"{len(js)} 个 bundle")

    refs = glob.glob(os.path.join(SKILL_DIR, "references", "phase-*.md"))
    check("7 阶段手册 references/phase-*.md", len(refs) >= 7,
          f"只有 {len(refs)} 个" if len(refs) < 7 else f"{len(refs)} 个齐全")

    if os.path.isdir(os.path.join(REPO, ".git")):
        r = subprocess.run(["git", "-C", REPO, "fsck", "--connectivity-only"],
                           capture_output=True, text=True)
        check("git 仓库完整性 (fsck)", r.returncode == 0, ((r.stderr or r.stdout).strip()[:120]) or "OK")
        head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", REPO, "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip()
        check("工作区与提交一致", not dirty,
              f"HEAD={head}，有本地改动（开发机正常；纯安装副本不该有）" if dirty else f"HEAD={head} 干净",
              fatal=False)
    else:
        check("git 安装（可校验完整性）", False,
              "非 git 安装：建议用 git clone 安装以便校验/更新", fatal=False)


def _load_env(path) -> dict:
    env = dict(os.environ)
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if k.startswith("export "):   # 兼容 `export KEY=VAL` 写法
                        k = k[len("export "):].strip()
                    env[k] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def check_image(no_image: bool):
    """③ 真出图：实际调用 gen.py 批量出 2 张，验证生图通路 + 批量并发都通。"""
    print("\n=== ③ 真出图（批量并发）===")
    gen = next((p for p in [
        os.path.expanduser("~/.claude/skills/openai-image-gen/scripts/gen.py"),
        os.path.join(REPO, "openai-image-gen", "scripts", "gen.py"),
    ] if os.path.isfile(p)), None)
    if not gen:
        check("生图脚本 gen.py 可定位", False, "找不到 openai-image-gen/scripts/gen.py")
        return
    envf = os.path.expanduser("~/.config/openai/env")
    if not os.path.isfile(envf):
        check("真出图 smoke", False, "无 ~/.config/openai/env（配 key 后才能真出图）", fatal=False)
        return
    if no_image:
        check("真出图 smoke", True, "按 --no-image 跳过（未实际调用 API）", fatal=False)
        return
    env = _load_env(envf)
    if not env.get("OPENAI_API_KEY"):
        check("真出图 smoke", False, "~/.config/openai/env 里没有 OPENAI_API_KEY", fatal=False)
        return
    tmp = tempfile.mkdtemp(prefix="pf-doctor-")
    try:
        # gen.py 的 --prompt 模式是「每个 --prompt 出一张」（这正是 ④页面批量的用法：一页一个 prompt）。
        # 给两个 prompt + --concurrency 2 → 并发出 2 张，验证「生图通路 + 批量并发」都通。
        r = subprocess.run(
            [sys.executable, gen, "--concurrency", "2",
             "--size", "1024x1024", "--model", "gpt-image-2", "--out-dir", tmp,
             "--prompt", "flat minimal gray square, simple UI test tile, no text",
             "--prompt", "flat minimal gray circle, simple UI test tile, no text"],
            capture_output=True, text=True, env=env, timeout=300)
        pngs = glob.glob(os.path.join(tmp, "*.png"))
        ok = r.returncode == 0 and len(pngs) >= 2 and all(os.path.getsize(p) > 1000 for p in pngs)
        if ok:
            detail = f"批量出 {len(pngs)} 张（生图通路 + 批量并发都通）"
        else:
            tail = ((r.stderr or r.stdout).strip().splitlines() or ["无输出"])[-1][:180]
            detail = f"只出 {len(pngs)} 张 / 失败：{tail}"
        check("真出图 smoke（批量 2 张）", ok, detail)
    except subprocess.TimeoutExpired:
        check("真出图 smoke（批量 2 张）", False, "超时（网络/网关慢，非致命）", fatal=False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="ProductFlow 深度自检 doctor")
    ap.add_argument("--no-image", action="store_true", help="跳过真出图（不调用付费 API）")
    args = ap.parse_args()

    print("ProductFlow 深度自检（doctor）\n" + "=" * 50)
    base = run_setup_baseline()
    check_completeness()
    check_image(args.no_image)

    print("\n" + "=" * 50)
    if issues or base != 0:
        extra = "；setup.py 基线未过（依赖/测试）" if base != 0 else ""
        print(f"{BAD} 深度自检未通过：{', '.join(issues) or '(见上)'}{extra}")
        return 1
    if warns:
        print(f"{OK} 核心 + 完整性 + 生图就绪。{len(warns)} 个可选项缺失（相关阶段降级，不挡）：{', '.join(warns)}")
    else:
        print(f"{OK} 全部通过：依赖 ✓ 测试 ✓ 代码完整 ✓ 真出图(批量) ✓")
    print("\n下一步 → 启动操作台：/productflow-start（或 sh scripts/start.sh）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
