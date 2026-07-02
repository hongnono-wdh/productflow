#!/usr/bin/env python3
"""ProductFlow pipeline state CLI. State lives in <project>/.productflow/."""

import argparse
import contextlib
import datetime as _dt
import json
import os
import re
import sys

try:
    import fcntl  # Unix 文件锁
except ImportError:  # Windows 无 fcntl——退化为单进程无锁（功能可用，仅并发安全降级）
    fcntl = None

PF_HOME = os.path.expanduser("~/.productflow")

PHASES = [
    {
        "id": 1,
        "name": "市场调研",
        "steps": [
            ("define-product", "明确产品与目标用户"),
            ("search-competitors", "竞品搜索与罗列网址"),
            ("analyze-style", "风格与卖点分析"),
            ("core-analysis", "核心矛盾分析"),
            ("replicate-report", "复刻要点报告"),
        ],
    },
    {
        "id": 2,
        "name": "找参考",
        "steps": [
            ("style-direction", "确定风格方向"),
            ("search-refs", "Dribbble 找参考"),
            ("select-refs", "选定参考"),
        ],
    },
    {
        "id": 3,
        "name": "首图设计",
        "steps": [
            ("gen-heroes", "生成首图候选"),
            ("pick-hero", "定首图·视觉基调"),
        ],
    },
    {
        "id": 4,
        "name": "页面设计",
        "steps": [
            ("page-map", "列出所有页面"),
            ("design-pages", "完成所有页面"),
            ("platform-versions", "各平台版本适配"),
            ("finalize-direction", "定稿设计方向"),
        ],
    },
    {
        "id": 5,
        "name": "功能与数据设计",
        "steps": [
            ("module-list", "功能模块清单"),
            ("er-diagram", "ER 图"),
            ("schema-ddl", "表结构 DDL"),
            ("api-contract", "API 契约"),
            ("pick-template", "选定开发模板"),
        ],
    },
    {
        "id": 6,
        "name": "开发实现",
        "steps": [
            ("scaffold", "脚手架搭建"),
            ("frontend", "前端实现"),
            ("backend", "后端实现"),
            ("testing", "测试"),
            ("api-docs", "接口文档"),
        ],
    },
    {
        "id": 7,
        "name": "部署上线",
        "steps": [
            ("pick-target", "选择部署目标"),
            ("deploy", "执行部署"),
            ("smoke-test", "冒烟测试"),
            ("handoff-report", "交付报告"),
        ],
    },
]

ARTIFACT_TYPES = {
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".svg": "image",
    ".md": "md", ".html": "html", ".sql": "code", ".json": "json",
}


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _root(d: str) -> str:
    return os.path.join(os.path.abspath(d), ".productflow")


def _state_path(d: str) -> str:
    return os.path.join(_root(d), "state.json")


@contextlib.contextmanager
def _locked(d: str):
    """整个 _load→改→_save 流程持有排他锁，防止与 server/其他 CLI 并发互踩。"""
    root = _root(d)
    if not os.path.isdir(root):
        raise SystemExit(f"no state at {_state_path(d)} — run init first")
    lf = open(os.path.join(root, ".lock"), "w")
    try:
        if fcntl is not None:
            fcntl.flock(lf, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(lf, fcntl.LOCK_UN)
        lf.close()


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "project"


def _registry_file(pid: str) -> str:
    return os.path.join(PF_HOME, "projects", pid + ".json")


def _read_registry_entry(pid: str):
    try:
        with open(_registry_file(pid), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _registry_upsert(pid: str, path: str) -> None:
    entry = _read_registry_entry(pid)
    if entry and entry.get("path") == path:
        return
    out = {
        "id": pid,
        "path": path,
        "created": (entry or {}).get("created", _now()),
        "archived": (entry or {}).get("archived", False),
        "v": 1,
    }
    os.makedirs(os.path.join(PF_HOME, "projects"), exist_ok=True)
    tmp = _registry_file(pid) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _registry_file(pid))


def _new_id(product: str, path: str) -> str:
    base = _slug(product)
    while True:
        pid = f"{base}-{os.urandom(2).hex()}"
        entry = _read_registry_entry(pid)
        # 同 id 已被其他路径占用 → 换随机后缀重试
        if entry is not None and entry.get("path") != path:
            continue
        if os.path.exists(_registry_file(pid)) and entry is None:
            continue  # 文件存在但读不出来，视为占用
        return pid


def _load(d: str) -> dict:
    path = _state_path(d)
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"no state at {path} — run init first")
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"state.json 已损坏，不是合法 JSON：{path}\n"
            f"  错误位置：第 {e.lineno} 行第 {e.colno} 列（{e.msg}）\n"
            f"  请手动修复该文件，或备份后重新执行 pf_state init --force"
        )
    # 自愈：旧版 state 缺 id/v → 补写并注册
    abspath = os.path.abspath(d)
    changed = False
    if not state.get("id"):
        state["id"] = _new_id(state.get("product", "project"), abspath)
        changed = True
    if "v" not in state:
        state["v"] = 1
        changed = True
    if changed:
        _save(d, state)
    _registry_upsert(state["id"], abspath)
    return state


def _save(d: str, state: dict) -> None:
    state["updated"] = _now()
    tmp = _state_path(d) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _state_path(d))


def _phase(state: dict, n: int) -> dict:
    for ph in state["phases"]:
        if ph["id"] == n:
            return ph
    raise SystemExit(f"phase {n} not found (1-7)")


def create_project(d: str, product: str, force: bool = False) -> str:
    """初始化项目，返回项目 id。供 cmd_init 与 server（向导直接创建）共用。"""
    root = _root(d)
    os.makedirs(os.path.join(root, "artifacts"), exist_ok=True)
    for ph in PHASES:
        os.makedirs(os.path.join(root, "artifacts", f"phase-{ph['id']}"), exist_ok=True)
    if os.path.exists(_state_path(d)) and not force:
        raise FileExistsError(f"state already exists at {_state_path(d)}")
    abspath = os.path.abspath(d)
    pid = _new_id(product, abspath)
    state = {
        "id": pid, "v": 1, "product": product, "project_dir": abspath,
        "created": _now(), "updated": _now(), "current_phase": 1,
        "phases": [
            {
                "id": ph["id"], "name": ph["name"], "status": "pending",
                "steps": [{"id": sid, "title": t, "status": "pending"} for sid, t in ph["steps"]],
                "artifacts": [],
            }
            for ph in PHASES
        ],
        "log": [{"ts": _now(), "msg": f"初始化项目「{product}」"}],
    }
    _save(d, state)
    _registry_upsert(pid, abspath)
    open(os.path.join(root, "inbox.jsonl"), "a", encoding="utf-8").close()
    return pid


def cmd_init(args) -> None:
    try:
        pid = create_project(args.dir, args.product, force=args.force)
    except FileExistsError:
        raise SystemExit(f"state already exists at {_state_path(args.dir)} (use --force to reset)")
    print(f"initialized {_root(args.dir)} (id: {pid})")


def cmd_status(args) -> None:
    s = _load(args.dir)
    print(f"{s['product']}  (phase {s['current_phase']}/7)  updated {s['updated']}")
    for ph in s["phases"]:
        mark = {"pending": "·", "active": "▶", "done": "✓"}.get(ph["status"], "?")
        steps = " ".join(
            {"pending": "○", "active": "◐", "done": "●", "skipped": "⊘"}.get(st["status"], "?")
            for st in ph["steps"]
        )
        print(f"  {mark} P{ph['id']} {ph['name']:8} {steps}  artifacts:{len(ph['artifacts'])}")


def cmd_phase(args) -> None:
    s = _load(args.dir)
    ph = _phase(s, args.n)
    # ⑥ 完工完整性闸：标 phase 6 done 前，④ 每个有设计稿的「页×平台」都要有带 page-id 的实现截图——
    # 缺页要么补做、要么 `page set <id> --impl-skip "原因"` 显式豁免，杜绝「漏页还标完成」。--force 可越闸（留痕）。
    if args.n == 6 and args.status == "done" and not getattr(args, "force", False):
        _c, missing, _s = _impl_coverage(args.dir)
        if missing:
            lines = "\n".join(f"  - {m['name']}（{m['platform'] or '通用'}） id={m['id']}" for m in missing)
            raise SystemExit(
                f"⑥ 还有 {len(missing)} 个页面只有 ④ 设计稿、没有 ⑥ 实现截图，不能标 done：\n{lines}\n"
                "→ 补做并 `artifact 6 <图> --page-id <id> --platform <PC|H5|APP>` 登记；"
                "确实本阶段不做的页用 `page set <id> --impl-skip \"原因\"` 显式豁免；"
                "或加 `--force` 强行标 done（不推荐，会留痕）。先跑 `impl-check` 看缺哪些。"
            )
    # 每次（重新）进入本阶段 = 新「一代」：之后登记的产物都带这个版本号，
    # 这样重做后产物画廊一眼看出哪批是哪一版（老批留痕、可对比）。只在 pending/done→active 时 +1。
    if args.status == "active" and ph.get("status") != "active":
        ph["gen"] = ph.get("gen", 0) + 1
    ph["status"] = args.status
    if args.status == "active":
        s["current_phase"] = args.n
    s["log"].append({"ts": _now(), "msg": f"P{args.n} {ph['name']} → {args.status}"})
    _save(args.dir, s)
    print(f"phase {args.n} = {args.status}")


def cmd_step(args) -> None:
    s = _load(args.dir)
    ph = _phase(s, args.n)
    for st in ph["steps"]:
        if st["id"] == args.step_id:
            st["status"] = args.status
            _save(args.dir, s)
            print(f"P{args.n}/{args.step_id} = {args.status}")
            return
    valid = ", ".join(st["id"] for st in ph["steps"])
    raise SystemExit(f"unknown step {args.step_id!r} in phase {args.n} (valid: {valid})")


def cmd_artifact(args) -> None:
    s = _load(args.dir)
    ph = _phase(s, args.n)
    rel = args.file.lstrip("/")
    full = os.path.join(_root(args.dir), rel)
    if not os.path.exists(full):
        raise SystemExit(f"artifact file not found: {full}")
    if args.type:
        atype = args.type
    elif rel.lower().endswith(".mm.md"):
        atype = "mindmap"
    else:
        atype = ARTIFACT_TYPES.get(os.path.splitext(rel)[1].lower(), "file")
    # 版本号 = 本阶段「第几代」（每次重做阶段 +1，见 cmd_phase）。同一代里登记的产物同号；
    # 重做后新登记的产物号 +1，老产物留痕——产物画廊据此分辨哪批是哪一版。未激活/老数据默认 v1。
    version = ph.get("gen") or 1
    ph["artifacts"] = [a for a in ph["artifacts"] if a["file"] != rel]
    rec = {"file": rel, "title": args.title, "type": atype, "ts": _now(), "version": version}
    # ⑥ 实现截图与 ④ 页面配对用：--page-id 关联某页（pages.json 的 pg-xxx）、--platform 标平台。
    # 都可选；带上后操作台「成品预览」能把「④设计图 ↔ ⑥实现图」按页并排对比（P6-5）。
    if getattr(args, "page_id", None):
        rec["pageId"] = args.page_id
    if getattr(args, "platform", None):
        rec["platform"] = args.platform.upper()
    ph["artifacts"].append(rec)
    s["log"].append({"ts": _now(), "msg": f"P{args.n} 产物：{args.title}（v{version}）"})
    _save(args.dir, s)
    print(f"registered {rel} (v{version})")


def cmd_artifact_rm(args) -> None:
    s = _load(args.dir)
    ph = _phase(s, args.n)
    rel = args.file.lstrip("/")
    before = len(ph["artifacts"])
    ph["artifacts"] = [a for a in ph["artifacts"] if a["file"] != rel]
    if before == len(ph["artifacts"]):
        print(f"not registered: {rel}")
        return
    if not args.keep_file:
        _rm_artifact_file(args.dir, rel)
    s["log"].append({"ts": _now(), "msg": f"P{args.n} 移除产物：{rel}"})
    _save(args.dir, s)
    print(f"unregistered {rel}" + ("" if args.keep_file else " (file deleted)"))


def _build_arch_md(data: dict) -> str:
    """把 arch.json（agent 产出的结构化页面树）**确定性地**组装成 markmap 大纲。
    图标由树中位置推导（顶层页=🗂 / 嵌套子页=📄 / 模块=🧩）、页面父子由 parent 字段嵌套——
    都由代码保证，不依赖 agent 手拼 markdown。agent 只需把每页的 parent 判对。"""
    product = str(data.get("product") or "产品").strip()
    pages = [p for p in (data.get("pages") or []) if isinstance(p, dict)]
    by_id = {str(p.get("id") or "").strip(): p for p in pages if str(p.get("id") or "").strip()}
    children: dict = {}
    for p in pages:
        par = p.get("parent")
        par = str(par).strip() if par else ""
        if par not in by_id:          # 悬空/无父 → 提到顶层
            par = ""
        children.setdefault(par, []).append(p)
    lines = [f"# {product}"]
    seen: set = set()

    def emit(p: dict, depth: int) -> None:
        pid = str(p.get("id") or "").strip()
        if pid in seen:               # 防父子成环
            return
        seen.add(pid)
        icon = "🗂" if depth <= 2 else "📄"   # 顶层页=一级/入口(🗂)，更深=子页(📄)
        name = str(p.get("name") or "").strip()
        if depth <= 6:
            lines.append(f"{'#' * depth} {icon} {name}")
        else:
            lines.append(f"{'  ' * (depth - 7)}- {icon} {name}")   # 过深兜底转列表
        for m in (p.get("modules") or []):
            if not isinstance(m, dict):
                continue
            lines.append(f"- 🧩 {str(m.get('name') or '').strip()}")
            for feat in (m.get("features") or []):
                lines.append(f"  - {str(feat).strip()}")
        for c in children.get(pid, []):
            emit(c, depth + 1)

    for top in children.get("", []):
        emit(top, 2)
    return "\n".join(lines).rstrip() + "\n"


def cmd_arch(args) -> None:
    """④ 业务架构树：读 .productflow/arch.json（agent 产出的结构化页面树）→ 代码组装
    module-arch.mm.md（类型图标 + 页面父子嵌套由代码保证正确）+ 登记为 phase-4 产物。"""
    root = _root(args.dir)
    ap = os.path.join(root, "arch.json")
    try:
        with open(ap, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise SystemExit("找不到 .productflow/arch.json（先让 agent 写好结构化页面树再 build）")
    except json.JSONDecodeError as e:
        raise SystemExit(f"arch.json 解析失败：{e}")
    rel = "artifacts/phase-4/module-arch.mm.md"
    os.makedirs(os.path.join(root, "artifacts", "phase-4"), exist_ok=True)
    with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
        f.write(_build_arch_md(data))
    s = _load(args.dir)               # 登记为 phase-4 产物（mindmap）
    ph = _phase(s, 4)
    version = ph.get("gen") or 1
    ph["artifacts"] = [a for a in ph["artifacts"] if a["file"] != rel]
    ph["artifacts"].append({"file": rel, "title": "业务模块架构", "type": "mindmap", "ts": _now(), "version": version})
    s["log"].append({"ts": _now(), "msg": f"P4 产物：业务模块架构（v{version}）"})
    _save(args.dir, s)
    print(f"业务架构树已组装并登记：{len(data.get('pages') or [])} 页 → {rel}")


def cmd_log(args) -> None:
    s = _load(args.dir)
    s["log"].append({"ts": _now(), "msg": args.msg})
    _save(args.dir, s)
    print("logged")


def cmd_reply(args) -> None:
    _load(args.dir)  # 校验项目存在 + 注册表自愈
    path = os.path.join(_root(args.dir), "inbox.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _now(), "from": "agent", "text": args.text},
                           ensure_ascii=False) + "\n")
    print("replied")


def cmd_inbox(args) -> None:
    _load(args.dir)  # 校验项目存在 + 注册表自愈
    root = _root(args.dir)
    path = os.path.join(root, "inbox.jsonl")
    cursor_path = os.path.join(root, "inbox.cursor")
    lines: list[str] = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    try:
        with open(cursor_path, encoding="utf-8") as f:
            cursor = int(f.read().strip() or "0")
    except (FileNotFoundError, ValueError):
        cursor = 0
    unread = []
    for i, ln in enumerate(lines):
        if i < cursor or not ln.strip():
            continue
        try:
            m = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if m.get("from") == "web":
            unread.append(m)
    if not lines:
        print("(inbox empty)")
    elif not unread:
        print("(no new messages)")
    for m in unread:
        print(f"[{m.get('ts', '')}] {m.get('text', '')}")
        if m.get("type") == "canvas-feedback":
            liked = m.get("liked") or []
            notes = m.get("notes") or []
            print(f"  ❤ liked ({len(liked)}):")
            for fp in liked:
                print(f"    - {fp}")
            print(f"  📝 notes ({len(notes)}):")
            for n in notes:
                print(f"    - {n}")
    if not args.peek:
        tmp = cursor_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(str(len(lines)))
        os.replace(tmp, cursor_path)


# ── 页面地图（画布顶部占位带）：pages.json 独立于 state.json ──

def _pages_path(d: str) -> str:
    return os.path.join(_root(d), "pages.json")


def _load_pages(d: str) -> dict:
    try:
        with open(_pages_path(d), encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("pages"), list):
                return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {"pages": []}


def _save_pages(d: str, data: dict) -> None:
    tmp = _pages_path(d) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _pages_path(d))


def _impl_coverage(d: str):
    """⑥ 实现覆盖：比对「④ 有设计稿的 (页 × 平台)」vs「⑥ 带 page-id 的实现截图」。
    返回 (covered, missing, skipped)——元素为 dict。无设计稿的页不参与（还没设计，不算 ⑥ 的账）；
    页设了 implSkip（显式声明本阶段不实现）→ 整页计入 skipped、不算缺。
    匹配：优先 (pageId, platform) 精确；截图没标 platform 时按页级兜底。"""
    pages = _load_pages(d)["pages"]
    s = _load(d)
    ph6 = next((p for p in s.get("phases", []) if p.get("id") == 6), {})
    impls = [a for a in ph6.get("artifacts", []) if a.get("type") == "image" and a.get("pageId")]
    have_pp = {(a.get("pageId"), (a.get("platform") or "").upper()) for a in impls if a.get("platform")}
    have_pg = {a.get("pageId") for a in impls if not a.get("platform")}  # 无平台标记 → 页级兜底
    covered, missing, skipped = [], [], []
    for p in pages:
        vers = [v for v in p.get("versions", []) if isinstance(v, dict) and v.get("file")]
        if not vers:
            continue
        if (p.get("implSkip") or "").strip():
            skipped.append({"id": p["id"], "name": p["name"], "reason": p["implSkip"].strip()})
            continue
        plats: list = []
        for v in vers:
            pl = (v.get("platform") or "").upper()
            if pl not in plats:
                plats.append(pl)
        for pl in plats:
            row = {"id": p["id"], "name": p["name"], "platform": pl}
            (covered if ((p["id"], pl) in have_pp or p["id"] in have_pg) else missing).append(row)
    return covered, missing, skipped


def cmd_impl_check(args) -> None:
    covered, missing, skipped = _impl_coverage(args.dir)
    if getattr(args, "json", False):
        print(json.dumps({"covered": covered, "missing": missing, "skipped": skipped}, ensure_ascii=False))
    else:
        total = len(covered) + len(missing)
        print(f"⑥ 实现覆盖校验：④ 设计稿共 {total} 个「页×平台」，已实现 {len(covered)}、缺 {len(missing)}、豁免 {len(skipped)}")
        if missing:
            print("❌ 缺实现（有 ④ 设计稿、无 ⑥ 带 page-id 的实现截图）：")
            for m in missing:
                print(f"   - {m['name']}（{m['platform'] or '通用'}）  id={m['id']}")
        if skipped:
            print("⏭ 已豁免（本阶段显式声明不实现）：")
            for m in skipped:
                print(f"   - {m['name']}：{m['reason']}")
        if missing:
            print("→ 补做并 `artifact 6 <图> --page-id <id> --platform <PC|H5|APP>` 登记；"
                  "确实本阶段不做的页用 `page set <id> --impl-skip \"原因\"` 豁免。")
        else:
            print("✅ 全部覆盖或已豁免，通过。")
    raise SystemExit(0 if not missing else 1)


def cmd_page(args) -> None:
    _load(args.dir)  # 校验项目存在 + 注册表自愈
    data = _load_pages(args.dir)
    pages = data["pages"]

    if args.action == "list":
        for p in pages:
            print(f"{p['id']}  [{p.get('status', 'placeholder')}]  "
                  f"{p.get('group', '')}/{p['name']}  versions:{len(p.get('versions', []))}")
        if not pages:
            print("(no pages)")
        return

    if args.action == "add":
        pg = {
            "id": "pg-" + os.urandom(3).hex(),
            "name": args.name,
            "group": args.group or "未分组",
            "status": args.status or "placeholder",
            "versions": [],
            "note": args.note or "",
        }
        pages.append(pg)
        _save_pages(args.dir, data)
        print(f"added page {pg['id']}: {pg['name']}")
        return

    pg = next((p for p in pages if p["id"] == args.id), None)
    if pg is None:
        raise SystemExit(f"page not found: {args.id}")

    if args.action == "rm":
        # 删整页 = 删占位符：连带删掉它的全部设计版本文件 + 清 canvas 位置（避免孤儿）
        for f in {v.get("file") for v in pg.get("versions", []) if isinstance(v, dict) and v.get("file")}:
            _rm_artifact_file(args.dir, f)
        data["pages"] = [p for p in pages if p["id"] != args.id]
        _save_pages(args.dir, data)
        _clean_canvas_page(args.dir, args.id)
        print(f"removed page {args.id}")
        return

    # set
    if args.name:
        pg["name"] = args.name
    if args.group:
        pg["group"] = args.group
    if args.note is not None:
        pg["note"] = args.note
    if getattr(args, "impl_skip", None) is not None:
        # ⑥ 覆盖校验豁免：声明该页本阶段不实现的原因；传空串清除豁免
        r = args.impl_skip.strip()
        if r:
            pg["implSkip"] = r
        else:
            pg.pop("implSkip", None)
    if args.add_version:
        plat = (args.platform or "").upper() or None   # PC / H5 / APP，或不分平台
        # versions 元素为 {file, platform}，支持"每页 × 平台"多版本；按 (file,platform) 去重
        if not any(isinstance(v, dict) and v.get("file") == args.add_version
                   and v.get("platform") == plat for v in pg["versions"]):
            pg["versions"].append({"file": args.add_version, "platform": plat})
        if pg.get("status") == "placeholder":
            pg["status"] = "done"  # 有了设计版本，占位自动转已设计
    if getattr(args, "remove_version", None):
        # 删单个设计版本（保留页面占位）。按 (file, platform) 匹配；文件不再被其它版本引用才删盘
        plat = (args.platform or "").upper() or None
        pg["versions"] = [v for v in pg["versions"]
                          if not (isinstance(v, dict) and v.get("file") == args.remove_version
                                  and (v.get("platform") or None) == plat)]
        if not any(isinstance(v, dict) and v.get("file") == args.remove_version for v in pg["versions"]):
            _rm_artifact_file(args.dir, args.remove_version)
        if pg.get("activeVersion") == args.remove_version:
            pg["activeVersion"] = pg["versions"][0]["file"] if pg["versions"] else ""
        if not pg["versions"]:
            pg["status"] = "placeholder"   # 删到没有任何版本 → 退回占位符
            pg.pop("activeVersion", None)
    if getattr(args, "active_version", None):
        pg["activeVersion"] = args.active_version   # 定稿版（多版本里挑一个作⑥开发取用）
    if args.status:
        pg["status"] = args.status  # 显式 --status 优先
    _save_pages(args.dir, data)
    print(f"updated page {args.id}")


# ── 视觉探索（向导第3步：Dribbble 参考 + 首图生成，人机协作）──

def _explore_path(d: str) -> str:
    return os.path.join(_root(d), "explore.json")


def _load_explore(d: str) -> dict:
    # request 按 kind 分槽：{"search-refs": {...}, "gen-heroes": {...}}——
    # P2 找参考与 P3 首图是两个阶段，单槽会互相覆盖、done-request 清错槽。
    base = {"stylePrefs": [], "request": {}, "refs": [], "selectedRefs": [],
            "styleSummary": "", "heroes": [], "selectedHero": "", "heroGenLog": [], "searchPlan": None}
    try:
        with open(_explore_path(d), encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                base.update(data)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    if not isinstance(base.get("request"), dict):  # 兼容旧的单槽/None
        base["request"] = {}
    return base


def _save_explore(d: str, data: dict) -> None:
    tmp = _explore_path(d) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _explore_path(d))


def _rm_artifact_file(d: str, rel: str) -> None:
    """安全删除一个 artifacts/ 下的文件（realpath 锚定，越界不删）。"""
    if not rel:
        return
    base = os.path.realpath(os.path.join(_root(d), "artifacts"))
    full = os.path.realpath(os.path.join(_root(d), rel))
    if full.startswith(base + os.sep):
        try:
            os.remove(full)
        except OSError:
            pass


def _clean_canvas_page(d: str, page_id: str) -> None:
    """删页面后清掉 canvas.json 里它的位置项（避免孤儿 page:<id>，画布不再残留幽灵卡）。"""
    if not page_id:
        return
    cpath = os.path.join(_root(d), "canvas.json")
    key = "page:" + str(page_id)
    try:
        with open(cpath, encoding="utf-8") as f:
            cdata = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return
    if not isinstance(cdata, dict):
        return
    changed = False
    for st in cdata.values():
        items = st.get("items") if isinstance(st, dict) else None
        if isinstance(items, dict) and key in items:
            del items[key]
            changed = True
    if changed:
        tmp = cpath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cdata, f, indent=2, ensure_ascii=False)
        os.replace(tmp, cpath)


def cmd_explore(args) -> None:
    _load(args.dir)  # 校验项目 + 自愈注册
    e = _load_explore(args.dir)

    if args.eaction == "show":
        print(json.dumps(e, ensure_ascii=False, indent=2))
        return
    if args.eaction == "add-ref":
        if os.path.splitext(args.file)[1].lower() not in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"):
            print(f"warning: {args.file} 不是图片扩展名，画廊按图片渲染会显示破图（仍照常登记）", file=sys.stderr)
        # 去重：第二/三轮找参考常抓到与前批相同的热门结果。同来源 URL（非空）或同文件路径
        # 一律跳过、不重复登记——保证画廊里参考不重复（exit 0，不打断 agent 流程）。
        src = (args.source or "").strip()
        dup = (src and any((r.get("source") or "").strip() == src for r in e["refs"])) \
            or any(r.get("file") == args.file for r in e["refs"])
        if dup:
            print(f"explore add-ref skipped（重复，未登记）: file={args.file} source={src or '-'}")
            return
        e["refs"].append({"id": "ref-" + os.urandom(3).hex(), "file": args.file,
                          "title": args.title or "", "source": args.source or "",
                          "desc": (getattr(args, "desc", "") or "")})
    elif args.eaction == "set-search-plan":   # 写「即将搜索的关键词清单 + 依据」，前端先呈现再搜
        kws = [k.strip() for k in (args.keyword or []) if k and k.strip()]
        e["searchPlan"] = {"keywords": kws, "basis": (args.basis or ""), "ts": _now()}
    elif args.eaction == "add-hero":
        e["heroes"].append({"id": "hero-" + os.urandom(3).hex(), "file": args.file,
                           "style": args.style or ""})
    elif args.eaction == "set-summary":
        e["styleSummary"] = args.text
    elif args.eaction == "select-refs":   # 设定选中的参考（按 ref id，喂给③首图）——headless/CLI 用，对齐网页选稿
        valid = {r.get("id") for r in e["refs"]}
        unknown = [i for i in args.ids if i not in valid]
        if unknown:
            raise SystemExit(f"unknown ref id(s): {', '.join(unknown)}")
        seen = set()
        e["selectedRefs"] = [i for i in args.ids if not (i in seen or seen.add(i))]
    elif args.eaction == "select-hero":   # 设定定稿首图（按 hero id，落库为其 file 路径，与 server 约定一致）
        hero = next((h for h in e["heroes"] if h.get("id") == args.id), None)
        if hero is None:
            valid = ", ".join(h.get("id", "") for h in e["heroes"]) or "(none)"
            raise SystemExit(f"unknown hero id {args.id!r} (valid: {valid})")
        e["selectedHero"] = hero.get("file", "")
    elif args.eaction == "remove-ref":
        ref = next((r for r in e["refs"] if r.get("id") == args.id), None)
        e["refs"] = [r for r in e["refs"] if r.get("id") != args.id]
        e["selectedRefs"] = [x for x in e.get("selectedRefs", []) if x != args.id]
        if ref:
            _rm_artifact_file(args.dir, ref.get("file"))
    elif args.eaction == "remove-hero":
        hero = next((h for h in e["heroes"] if h.get("id") == args.id), None)
        e["heroes"] = [h for h in e["heroes"] if h.get("id") != args.id]
        if hero and e.get("selectedHero") == hero.get("file"):
            e["selectedHero"] = ""
        if hero:
            _rm_artifact_file(args.dir, hero.get("file"))
    elif args.eaction == "done-request":
        req = e.get("request")
        if not isinstance(req, dict):
            e["request"] = {}
        elif getattr(args, "kind", None):
            req.pop(args.kind, None)   # 只清这一类（如 search-refs），不动另一阶段的请求
        else:
            e["request"] = {}          # 缺省清全部
    elif args.eaction == "gen-record":
        # 记一条「生成首图」记录，供 ③ 画布对话框展示：用了哪些参考 + 发了什么 prompt + 出了哪几张
        rec = {"ts": _now(), "mode": args.mode or "gen",
               "refs": args.refs or [], "prompt": args.prompt or "", "results": args.results or []}
        if not isinstance(e.get("heroGenLog"), list):
            e["heroGenLog"] = []
        e["heroGenLog"].append(rec)
        e["heroGenLog"] = e["heroGenLog"][-40:]   # 防无界增长：只留最近 40 条生成记录
    elif args.eaction == "clear":
        e = {"stylePrefs": [], "request": {}, "refs": [], "selectedRefs": [],
             "styleSummary": "", "heroes": [], "selectedHero": "", "heroGenLog": []}
    _save_explore(args.dir, e)
    print(f"explore {args.eaction} ok")


# ── 选项确认（通用：Agent 在任意阶段抛"待确认问题+选项"，用户在网页点选答复）──

def _choices_path(d: str) -> str:
    return os.path.join(_root(d), "choices.json")


def _load_choices(d: str) -> dict:
    base = {"choices": []}
    try:
        with open(_choices_path(d), encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("choices"), list):
                base = data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return base


def _save_choices(d: str, data: dict) -> None:
    tmp = _choices_path(d) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _choices_path(d))


def cmd_choice(args) -> None:
    _load(args.dir)
    c = _load_choices(args.dir)
    if args.caction == "show":
        print(json.dumps(c, ensure_ascii=False, indent=2))
        return
    if args.caction == "ask":
        ch = {"id": "ch-" + os.urandom(3).hex(), "stage": args.stage,
              "question": args.question, "options": args.option or [],
              "answer": None, "ts": _now()}
        c["choices"].append(ch)
        _save_choices(args.dir, c)
        # 投 inbox 让用户在网页/CLI 都能看到这是一条待确认
        try:
            with open(os.path.join(_root(args.dir), "inbox.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": _now(), "from": "agent", "type": "choice",
                                    "text": "待你确认：" + args.question}, ensure_ascii=False) + "\n")
        except OSError:
            pass
        print(ch["id"])
        return
    if args.caction == "answer":   # 主要给 CLI/测试；前端走 server /api/choice
        for ch in c["choices"]:
            if ch["id"] == args.id:
                ch["answer"] = args.text
        _save_choices(args.dir, c)
        print("ok")
        return
    if args.caction == "wait":   # 阻塞轮询直到该 choice 被答复或超时——headless agent 用它真正「等用户点选」
        import time as _t
        deadline = _t.monotonic() + max(1, int(args.timeout or 600))
        while True:
            cur = _load_choices(args.dir)
            ch = next((x for x in cur["choices"] if x["id"] == args.id), None)
            if ch is None:
                print(json.dumps({"error": "no_such_choice", "id": args.id}, ensure_ascii=False))
                return
            if ch.get("answer") is not None:
                print(json.dumps(ch, ensure_ascii=False))   # 已答复：打印整条（含 answer）供 agent 解析
                return
            if _t.monotonic() >= deadline:
                print(json.dumps({"timeout": True, **ch}, ensure_ascii=False))   # 超时：answer 仍为 null
                return
            _t.sleep(3)


# ── 产品需求摘要（向导第2步：CLI 生成 AI 理解摘要回填）──

def _brief_path(d: str) -> str:
    return os.path.join(_root(d), "brief.json")


def _load_brief(d: str) -> dict:
    base = {"description": "", "request": None, "questions": [], "confirmed": False,
            "summary": {"goal": "", "users": "", "need": "", "scope": ""}, "ready": False, "history": []}
    try:
        with open(_brief_path(d), encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                base.update(data)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return base


def cmd_brief(args) -> None:
    _load(args.dir)
    b = _load_brief(args.dir)
    if args.baction == "show":
        print(json.dumps(b, ensure_ascii=False, indent=2))
        return
    if args.baction == "set-summary":
        b["summary"] = {"goal": args.goal or "", "users": args.users or "",
                        "need": args.need or "", "scope": args.scope or ""}
        b["ready"] = True
        b["request"] = None  # 生成完即清请求，前端轮询到 ready=true 回填摘要
    elif args.baction == "done-request":
        b["request"] = None
    tmp = _brief_path(args.dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(b, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _brief_path(args.dir))
    print(f"brief {args.baction} ok")


def set_product(d: str, product: str) -> None:
    """更新项目显示名（state.product）。不动 id/dir/注册表（都按 id），改名安全。
    供 server 的 /api/project-config 与 cmd_meta 共用。"""
    state = _load(d)
    state["product"] = product
    _save(d, state)  # _save 自动刷新 updated


def cmd_meta(args) -> None:
    if args.product is not None:
        name = args.product.strip() or "未命名项目"
        set_product(args.dir, name)
        print(f"product = {name}")
    else:
        print("meta: 无改动（用 --product 改显示名）")


def cmd_unregister(args) -> None:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", args.id):
        raise SystemExit(f"invalid project id: {args.id!r}")
    fp = _registry_file(args.id)
    if not os.path.exists(fp):
        raise SystemExit(f"no registry entry for {args.id!r} at {fp}")
    os.remove(fp)
    print(f"unregistered {args.id} (project files untouched)")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pf_state", description="ProductFlow pipeline state")
    # 默认取环境变量 PF_PROJECT（启动时 export 一次，全程命令免写 --dir，避免落错目录）；都没有才退到 cwd
    p.add_argument("--dir", default=os.environ.get("PF_PROJECT") or ".",
                   help="project directory (default: $PF_PROJECT, else cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init")
    sp.add_argument("--product", required=True)
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_init)

    sp = sub.add_parser("status")
    sp.set_defaults(fn=cmd_status)

    sp = sub.add_parser("phase")
    sp.add_argument("n", type=int)
    sp.add_argument("--status", required=True, choices=["pending", "active", "done"])
    sp.add_argument("--force", action="store_true", help="越过 ⑥ 实现覆盖闸强行标 done（留痕，不推荐）")
    sp.set_defaults(fn=cmd_phase)

    # ⑥ 实现覆盖校验：④ 每个有设计稿的「页×平台」是否都有带 page-id 的实现截图（缺页 → 退出码 1）
    sp = sub.add_parser("impl-check", help="⑥ 校验：④ 设计稿页×平台是否都有带 page-id 的 ⑥ 实现截图；缺则非 0 退出")
    sp.add_argument("n", type=int, nargs="?", default=6, help="阶段号（当前固定校验 ⑥，默认 6）")
    sp.add_argument("--json", action="store_true", help="输出 JSON（covered/missing/skipped）")
    sp.set_defaults(fn=cmd_impl_check)

    sp = sub.add_parser("step")
    sp.add_argument("n", type=int)
    sp.add_argument("step_id")
    sp.add_argument("--status", required=True, choices=["pending", "active", "done", "skipped"])
    sp.set_defaults(fn=cmd_step)

    sp = sub.add_parser("artifact")
    sp.add_argument("n", type=int)
    sp.add_argument("file", help="path relative to .productflow/ (e.g. artifacts/phase-1/x.png)")
    sp.add_argument("--title", required=True)
    sp.add_argument("--type", default=None)
    sp.add_argument("--page-id", dest="page_id", help="（⑥实现截图用）关联 ④ 的某个页面 id（pages.json 的 pg-xxx），供操作台按页配对「设计图↔实现图」")
    sp.add_argument("--platform", choices=["PC", "H5", "APP"], help="（⑥实现截图用）该截图对应的平台，配合 --page-id 精确配对")
    sp.set_defaults(fn=cmd_artifact)

    sp = sub.add_parser("artifact-rm", help="撤销登记一个产物（默认连磁盘文件一起删；--keep-file 只撤销登记）")
    sp.add_argument("n", type=int)
    sp.add_argument("file", help="要移除的产物路径，相对 .productflow/（如 artifacts/phase-6/preview-home.png）")
    sp.add_argument("--keep-file", action="store_true", help="只从状态撤销登记，保留磁盘文件")
    sp.set_defaults(fn=cmd_artifact_rm)

    # ④ 业务架构树：读 arch.json → 代码组装 module-arch.mm.md（图标+页面父子嵌套由代码保证）
    sp = sub.add_parser("arch", help='④ 业务架构树：读 .productflow/arch.json → 组装并登记 module-arch.mm.md')
    asub = sp.add_subparsers(dest="aaction", required=True)
    asub.add_parser("build", help="从 arch.json 确定性组装带图标+父子嵌套的架构树并登记")
    sp.set_defaults(fn=cmd_arch)

    sp = sub.add_parser("log")
    sp.add_argument("msg")
    sp.set_defaults(fn=cmd_log)

    sp = sub.add_parser("reply")
    sp.add_argument("text", help="message appended to inbox.jsonl as from=agent")
    sp.set_defaults(fn=cmd_reply)

    sp = sub.add_parser("inbox")
    sp.add_argument("--peek", action="store_true", help="read without advancing cursor")
    sp.set_defaults(fn=cmd_inbox)

    # page：项目应有页面的地图（画布顶部占位带）。status: placeholder|designing|done
    STATUSES = ["placeholder", "designing", "done"]
    sp = sub.add_parser("page")
    psub = sp.add_subparsers(dest="action", required=True)
    pa = psub.add_parser("add", help="加一个页面（默认占位 placeholder）")
    pa.add_argument("name")
    pa.add_argument("--group", help="所属模块分组，如「登录模块」「首页」")
    pa.add_argument("--note", help="AI 推断依据 / 页面说明")
    pa.add_argument("--status", choices=STATUSES)
    psub.add_parser("list", help="列出所有页面")
    pr = psub.add_parser("rm", help="删除页面")
    pr.add_argument("id")
    ps = psub.add_parser("set", help="更新页面：改名/分组/状态/加设计版本")
    ps.add_argument("id")
    ps.add_argument("--name")
    ps.add_argument("--group")
    ps.add_argument("--note")
    ps.add_argument("--status", choices=STATUSES)
    ps.add_argument("--add-version", help="关联一个设计产物文件（相对 .productflow/），多版本可多次加")
    ps.add_argument("--remove-version", help="移除一个设计版本（保留页面占位；删到空自动退回 placeholder）")
    ps.add_argument("--active-version", help="设为定稿版本（多版本里挑一个，⑥开发优先取用）")
    ps.add_argument("--platform", choices=["PC", "H5", "APP"], help="该版本对应的平台（配合 --add-version / --remove-version）")
    ps.add_argument("--impl-skip", dest="impl_skip", help="（⑥用）声明该页本阶段不实现的原因；写了则 ⑥ 覆盖校验豁免该页。传空串 '' 清除豁免")
    sp.set_defaults(fn=cmd_page)

    # explore：视觉探索（agent 写 Dribbble 参考 / 首图 / 风格总结）
    sp = sub.add_parser("explore")
    esub = sp.add_subparsers(dest="eaction", required=True)
    esub.add_parser("show", help="打印 explore.json（查看前端请求与当前状态）")
    er = esub.add_parser("add-ref", help="登记一张 Dribbble 参考图")
    er.add_argument("file", help="参考图路径，相对 .productflow/（如 artifacts/phase-2/refs/x.png）")
    er.add_argument("--title")
    er.add_argument("--source", help="来源 URL")
    er.add_argument("--desc", help="图片解析后的文本描述（风格/品类/含什么），供用户和③首图参考")
    esp = esub.add_parser("set-search-plan", help="写本轮即将搜索的关键词清单+依据（前端先呈现再搜）")
    esp.add_argument("--keyword", action="append", help="搜索关键词，可重复")
    esp.add_argument("--basis", help="一句话依据（来自市场调研：产品类型/风格方向等）")
    eh = esub.add_parser("add-hero", help="登记一张生成的首图")
    eh.add_argument("file")
    eh.add_argument("--style", help="该首图的风格名/描述")
    es = esub.add_parser("set-summary", help="写风格总结")
    es.add_argument("text")
    esel = esub.add_parser("select-refs", help="设定选中的参考（按 ref id，可多个；喂给③首图）")
    esel.add_argument("ids", nargs="+", help="一个或多个 ref id（来自 explore show 的 refs[].id）")
    eselh = esub.add_parser("select-hero", help="设定定稿首图（按 hero id；落库为其 file 路径）")
    eselh.add_argument("id", help="hero id（来自 explore show 的 heroes[].id）")
    erm = esub.add_parser("remove-ref", help="删除一张参考图（含磁盘文件）")
    erm.add_argument("id")
    ehm = esub.add_parser("remove-hero", help="删除一张首图（含磁盘文件）")
    ehm.add_argument("id")
    ed = esub.add_parser("done-request", help="标记前端请求已处理（前端轮询到即知完成）")
    ed.add_argument("--kind", help="只清这一类请求（search-refs/gen-heroes）；缺省清全部")
    egr = esub.add_parser("gen-record", help="记一条生成首图记录（用了哪些参考+发了什么 prompt+出了哪几张），供③对话框展示")
    egr.add_argument("--mode", choices=["gen", "edit"], help="gen=按参考生成 / edit=改某张图")
    egr.add_argument("--prompt", help="本次发给模型的完整 prompt 文字")
    egr.add_argument("--refs", nargs="*", help="本次引用的参考图（文件路径或 ref id），可多个")
    egr.add_argument("--results", nargs="*", help="本次产出的图文件，可多个")
    esub.add_parser("clear", help="清空视觉探索数据重来")
    sp.set_defaults(fn=cmd_explore)

    # choice：通用选项确认——Agent 抛"待确认问题+选项"，用户在网页点选答复
    sp = sub.add_parser("choice")
    csub = sp.add_subparsers(dest="caction", required=True)
    csub.add_parser("show", help="打印 choices.json（读用户的答复）")
    ca = csub.add_parser("ask", help="抛一个待确认问题给用户点选")
    ca.add_argument("--stage", type=int, help="所属阶段号 1-7")
    ca.add_argument("--question", required=True, help="问题文本")
    ca.add_argument("--option", action="append", help="一个选项（可多次给，2-4 个）")
    can = csub.add_parser("answer", help="替用户写答复（一般前端做，CLI/测试用）")
    can.add_argument("id")
    can.add_argument("--text", required=True)
    cw = csub.add_parser("wait", help="阻塞等用户答复某条 choice（headless agent 用）")
    cw.add_argument("id")
    cw.add_argument("--timeout", type=int, default=600, help="最多等多少秒（默认 600）")
    sp.set_defaults(fn=cmd_choice)

    # brief：产品需求摘要（向导第2步 AI 理解摘要，CLI 生成回填）
    sp = sub.add_parser("brief")
    bsub = sp.add_subparsers(dest="baction", required=True)
    bsub.add_parser("show", help="打印 brief.json（查看产品描述与请求）")
    bs = bsub.add_parser("set-summary", help="写 AI 理解摘要（4 项）")
    bs.add_argument("--goal", help="产品目标")
    bs.add_argument("--users", help="目标用户")
    bs.add_argument("--need", help="核心需求")
    bs.add_argument("--scope", help="输出范围")
    bsub.add_parser("done-request", help="标记请求已处理")
    sp.set_defaults(fn=cmd_brief)

    # meta：改项目显示名（向导重入时「创建项目」步可改名，slug/目录不变）
    sp = sub.add_parser("meta")
    sp.add_argument("--product", help="新的项目显示名")
    sp.set_defaults(fn=cmd_meta)

    sp = sub.add_parser("unregister")
    sp.add_argument("id", help="project id; removes registry entry only, project files untouched")
    sp.set_defaults(fn=cmd_unregister)

    args = p.parse_args(argv)
    if args.cmd == "unregister":
        args.fn(args)
        return 0
    if args.cmd == "init":
        os.makedirs(_root(args.dir), exist_ok=True)  # 锁文件所在目录需先存在
    with _locked(args.dir):
        args.fn(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
