"""Adversarial e2e harness — drives the React console as a hostile/clumsy user.

Multi-instance by design: each invocation spins its OWN sandboxed server
(helpers.start_server, free port) + its OWN browser, so it never collides with
the user's live :7717 or with a concurrently-running instance (Loop 1 vs Loop 2).
Playwright sync API is NOT thread-safe → concurrency = separate PROCESSES, which
is exactly how the two loops run.

Usage:
    python3 harness.py --persona impatient        # one persona, accumulate findings
    python3 harness.py --persona auto             # rotate persona by run counter

Journeys are grounded in the business flows in .understand-anything/domain-graph.json
(see PLAN.md). Each journey records findings on anomaly and NEVER crashes the run.
"""
import argparse
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, TESTS)   # tests/helpers.py
sys.path.insert(0, HERE)    # this dir: findings.py
import helpers as h  # noqa: E402
import findings as F  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
    _PW = True
except Exception:
    _PW = False

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000100ffff0300000006"
    "0005a3b8c4ad0000000049454e44ae426082"
)

# persona → behavior knobs
PERSONAS = {
    "impatient":   {"rapid_click": True},
    "overflow":    {"long_input": True},
    "flaky-net":   {"reload_mid": True},
    "multi-tab":   {"second_tab": True},
    "keyboard":    {"keyboard_only": True},
    "canvas-power": {"canvas_stress": True},
    "edge-empty":  {"empty": True},
    "skipper":     {"skip_prereq": True},
}
ROTATION = list(PERSONAS.keys())
_COUNTER = os.path.join(HERE, "findings", ".run-counter")


def _next_persona() -> str:
    n = 0
    try:
        n = int(open(_COUNTER).read().strip())
    except (OSError, ValueError):
        pass
    try:
        os.makedirs(os.path.dirname(_COUNTER), exist_ok=True)
        open(_COUNTER, "w").write(str(n + 1))
    except OSError:
        pass
    return ROTATION[n % len(ROTATION)]


class Ctx:
    def __init__(self, browser, port, home, persona, knobs):
        self.browser = browser
        self.port = port
        self.home = home
        self.persona = persona
        self.knobs = knobs
        self.console = []
        self.page = browser.new_page(viewport={"width": 1280, "height": 900})
        self.page.on("console", lambda m: self.console.append(m.text) if m.type == "error" and "404" not in m.text else None)
        self.page.on("pageerror", lambda e: self.console.append("pageerror: " + str(e)))

    def shot(self, name):
        p = os.path.join(HERE, "findings", f"{self.persona}-{name}.png")
        try:
            self.page.screenshot(path=p)
            return p
        except Exception:
            return None

    def record(self, journey, stage, severity, title, repro, observed, expected, name=""):
        F.add(self.persona, journey, stage, severity, title, repro, observed, expected,
              console_errors=self.console[-6:], screenshot=self.shot(name or journey))

    def art(self, pdir, rel):
        full = os.path.join(pdir, ".productflow", rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(_PNG)

    def url(self, path=""):
        return f"http://127.0.0.1:{self.port}{path}"


# ───────────────────────── journeys (grounded in domain-graph) ─────────────────────────

def j_create(ctx: Ctx):
    """Create project (name+platform only). overflow→long CJK name; impatient→double-click create."""
    pg = ctx.page
    pg.goto(ctx.url("/"), wait_until="networkidle")
    pg.wait_for_timeout(1500)
    if not pg.query_selector("#root"):
        ctx.record("create", "home", "broken", "默认 UI 不是 React 构建", ["打开 /"], "无 #root", "React dist")
        return None
    pg.click("button:has-text('新建项目')")
    pg.wait_for_selector("#new-modal.show", timeout=8000)
    name = ("超长产品名称测试" * 6 + "🚀<script>x</script>") if ctx.knobs.get("long_input") else "对抗测试项目"
    pg.fill("#nm-name", name)
    slug = "adv-" + ctx.persona
    pg.fill("#nm-slug", slug)
    pg.click("#new-modal .wz-pcard >> nth=2")  # toggle APP on
    btn = "#new-modal button:has-text('创建项目')"
    pg.click(btn)
    if ctx.knobs.get("rapid_click"):
        try:
            pg.click(btn, timeout=600)  # double-fire: must not create two / not crash
        except Exception:
            pass
    try:
        pg.wait_for_url(lambda u: "/p/" in u, timeout=10000)
    except Exception:
        ctx.record("create", "home", "broken", "创建后未跳转项目页", [f"新建 name={name[:20]}"], "URL 仍在首页", "跳到 /p/<id>/")
        return None
    pid = pg.url.rstrip("/").split("/")[-1]
    pdir = os.path.join(ctx.home, "code", slug)
    try:
        pg.wait_for_function("() => document.querySelectorAll('#stepper .step-pill').length === 7", timeout=12000)
    except Exception:
        ctx.record("create", "project", "broken", "项目页未渲染 7 阶段", [f"进入 {pid}"], "stepper 非 7 胶囊", "7 个 .step-pill")
    return pid, pdir


def j_navigate(ctx: Ctx, pid):
    """skipper: jump across all 7 stages; assert board|canvas renders + no console errors."""
    pg = ctx.page
    order = [7, 1, 4, 2, 6, 3, 5] if ctx.knobs.get("skip_prereq") else list(range(1, 8))
    for sid in order:
        try:
            pg.click(f"#stepper .step-pill >> nth={sid - 1}")
            pg.wait_for_timeout(250)
            canvas = sid in (3, 4)
            sel = "#view-canvas" if canvas else "#view-board"
            if not pg.query_selector(sel):
                ctx.record("navigate", f"P{sid}", "broken", f"阶段{sid}未渲染{'画布' if canvas else '看板'}",
                           [f"点 stepper 第{sid}个"], f"无 {sel}", f"{sel} 出现")
        except Exception as e:
            ctx.record("navigate", f"P{sid}", "crash", f"切到阶段{sid}抛异常", [f"点 stepper 第{sid}个"], str(e)[:120], "正常切换")
    if ctx.console:
        ctx.record("navigate", "all", "broken", "导航过程中有 console 报错", ["逐个切 7 阶段"], "; ".join(ctx.console[:3]), "0 console error")


def j_brief_focus_guard(ctx: Ctx, pid, pdir):
    """① brief：打字时后台推送不得抢焦点；confirm-lag。"""
    pg = ctx.page
    pg.click("#stepper .step-pill >> nth=0")
    try:
        pg.wait_for_selector("#stage-extra textarea", timeout=8000)
    except Exception:
        ctx.record("brief", "P1", "broken", "①面板无需求输入框", ["进①"], "无 textarea", "产品需求 textarea")
        return
    ta = pg.query_selector("#stage-extra textarea")
    ta.click()
    typed = "一个每月寄到家的精品手冲咖啡订阅" + ("，" + "超长澄清" * 30 if ctx.knobs.get("long_input") else "")
    ta.type(typed[:80], delay=10)
    pg.wait_for_timeout(1600)  # let WS push tick while focused
    val = pg.eval_on_selector("#stage-extra textarea", "e=>e.value") if pg.query_selector("#stage-extra textarea") else ""
    focused = pg.evaluate("() => document.activeElement && document.activeElement.tagName === 'TEXTAREA'")
    if typed[:40] not in (val or ""):
        ctx.record("brief", "P1", "broken", "打字内容被后台推送清掉(focus-guard 失效)", ["①输入框打字，等 WS 推送"], f"value={val[:30]!r}", "输入保留")
    if not focused:
        ctx.record("brief", "P1", "broken", "打字时焦点被推送抢走", ["①输入框打字，等 WS 推送"], "activeElement 非 textarea", "焦点保持")


def j_canvas(ctx: Ctx, pid, pdir):
    """③/④ 画布：拖拽持久化 + per-stage 隔离（canvas-power）。"""
    # backfill heroes so the canvas has cards
    ctx.art(pdir, "artifacts/phase-3/heroes/h0.png")
    h.cli(["explore", "add-hero", "artifacts/phase-3/heroes/h0.png", "--style", "s0"], ctx.home, project=pdir)
    pg = ctx.page
    pg.click("#stepper .step-pill >> nth=2")  # stage 3
    try:
        pg.wait_for_function("() => document.querySelectorAll('#cv-world .cv-item').length >= 1", timeout=12000)
    except Exception:
        ctx.record("canvas", "P3", "broken", "③画布首图卡未铺出", ["③ + add-hero"], "无 .cv-item", "至少 1 张卡(已修 isLoaded 竞态)")
        return
    card = pg.query_selector("#cv-world .cv-item")
    cid = card.get_attribute("data-id")
    box = card.bounding_box()
    if box:
        pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        pg.mouse.down()
        pg.mouse.move(box["x"] + 140, box["y"] + 90, steps=6)
        pg.mouse.up()
        pg.wait_for_timeout(950)  # debounce 600ms
    c3 = pg.evaluate("async () => (await (await fetch(location.pathname.replace(/\\/$/,'')+'/api/canvas?stage=3')).json())")
    if cid not in (c3.get("items") or {}):
        ctx.record("canvas", "P3", "broken", "③拖拽布局未持久化", ["③拖卡片，查 /api/canvas?stage=3"], "items 缺该卡", "坐标已存")
    # isolation: stage 4 canvas must not have the hero item
    pg.click("#stepper .step-pill >> nth=3")
    pg.wait_for_timeout(800)
    c4 = pg.evaluate("async () => (await (await fetch(location.pathname.replace(/\\/$/,'')+'/api/canvas?stage=4')).json())")
    if cid in (c4.get("items") or {}):
        ctx.record("canvas", "P4", "broken", "③画布卡串到④(per-stage 隔离失效)", ["③拖卡→切④查 stage=4"], "stage4 含 hero 卡", "两阶段隔离")


def j_run_stage_concurrency(ctx: Ctx, pid, pdir):
    """⑥ run-stage 并发护栏：连点不得双触发/崩（impatient/skipper）。"""
    pg = ctx.page
    pg.click("#stepper .step-pill >> nth=4")  # stage 5 (panel)
    try:
        pg.wait_for_selector("#stage-extra button:has-text('让 Agent 做本阶段')", timeout=8000)
    except Exception:
        ctx.record("run-stage", "P5", "broken", "⑤面板无 run-stage 按钮", ["进⑤"], "无按钮", "让 Agent 做本阶段")
        return
    b = "#stage-extra button:has-text('让 Agent 做本阶段')"
    pg.click(b)
    if ctx.knobs.get("rapid_click") or ctx.knobs.get("skip_prereq"):
        for _ in range(3):
            try:
                pg.click(b, timeout=400)
            except Exception:
                pass
    pg.wait_for_timeout(400)
    # the no-op claude stub finishes instantly; just assert no crash + inbox got the request
    out = h.cli(["inbox"], ctx.home, project=pdir).stdout
    if "阶段5" not in out:
        ctx.record("run-stage", "P5", "degraded", "run-stage 未写 inbox 请求", ["⑤点让Agent做本阶段"], "inbox 无 阶段5", "inbox 有 stage-request")


def j_chat(ctx: Ctx, pid, pdir):
    """聊天抽屉：发特殊/长消息 → 入 inbox、UI 不崩（overflow）。"""
    pg = ctx.page
    if not pg.query_selector("#chat-btn"):
        return
    pg.click("#chat-btn")
    try:
        pg.wait_for_selector("#chat-drawer.open", timeout=6000)
    except Exception:
        ctx.record("chat", "*", "broken", "聊天抽屉打不开", ["点💬留言"], "无 .open", "抽屉滑出")
        return
    msg = ("反馈" + "很长很长" * 40) if ctx.knobs.get("long_input") else "把首图改成暖色调 <b>test</b>"
    pg.fill("#chat-input", msg)
    pg.click("#chat-form button[type='submit']")
    pg.wait_for_timeout(400)
    out = h.cli(["inbox"], ctx.home, project=pdir).stdout
    if msg[:8] not in out:
        ctx.record("chat", "*", "broken", "聊天消息未进 inbox", [f"发消息 {msg[:20]}"], "inbox 无该消息", "消息入收件箱")
    # close the drawer so it doesn't cover topbar controls for the next journey
    try:
        pg.click("#chat-drawer >> text=收起", timeout=2000)
    except Exception:
        pass


def j_modals(ctx: Ctx, pid, pdir):
    """全部产物 overview modal 打开 + Esc 关闭。"""
    pg = ctx.page
    btn = pg.query_selector("button[title='一屏看全项目所有产物']")
    if not btn:
        return
    btn.click()
    try:
        pg.wait_for_selector("#modal.show", timeout=6000)
    except Exception:
        ctx.record("modal", "*", "broken", "全部产物 modal 打不开", ["点📋全部产物"], "无 #modal.show", "modal 弹出")
        return
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    if pg.query_selector("#modal.show"):
        ctx.record("modal", "*", "cosmetic", "Esc 未关闭 modal", ["开 modal 按 Esc"], "modal 仍在", "Esc 关闭")


def _reset_ui(ctx: Ctx):
    """Clean shared-page state between journeys (close overlays) so one journey's
    leftover (open drawer/modal) doesn't break the next — keeps findings attributable."""
    pg = ctx.page
    try:
        pg.keyboard.press("Escape")  # close modal / preview overlay
    except Exception:
        pass
    try:
        if pg.query_selector("#chat-drawer.open"):
            # close via the drawer's own 收起 control (on top); #chat-btn is covered by the drawer
            try:
                pg.click("#chat-drawer >> text=收起", timeout=2000)
            except Exception:
                pg.evaluate("() => { const d=document.getElementById('chat-drawer'); if(d) d.classList.remove('open'); }")
    except Exception:
        pass
    pg.wait_for_timeout(150)


def run(persona: str):
    knobs = PERSONAS.get(persona, {})
    home = h.make_home()
    proc = None
    pw = None
    browser = None
    try:
        proc, port = h.start_server(home)  # default React dist, own free port → multi-instance
        pw = sync_playwright().start()
        browser = pw.chromium.launch(executable_path=h.CHROMIUM_EXE, headless=True)
        ctx = Ctx(browser, port, home, persona, knobs)
        created = j_create(ctx)
        if created:
            pid, pdir = created
            for jfn in (j_navigate, j_brief_focus_guard, j_canvas, j_run_stage_concurrency, j_chat, j_modals):
                try:
                    _reset_ui(ctx)
                    ctx.console.clear()  # clean slate so this journey's console errors attribute correctly
                    if jfn is j_navigate:
                        jfn(ctx, pid)
                    else:
                        jfn(ctx, pid, pdir)
                except Exception as e:
                    ctx.record(jfn.__name__, "*", "crash", f"journey {jfn.__name__} 抛异常",
                               ["运行该 journey"], (str(e) + "\n" + traceback.format_exc())[:300], "journey 正常完成")
        print(json.dumps({"persona": persona, "summary": F.summary()}, ensure_ascii=False))
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if pw:
            try:
                pw.stop()
            except Exception:
                pass
        if proc:
            h.stop_server(proc)
        h.rm_home(home)


def main():
    if not _PW or not os.path.exists(h.CHROMIUM_EXE):
        print("SKIP: playwright/chromium unavailable")
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", default="auto")
    args = ap.parse_args()
    persona = _next_persona() if args.persona == "auto" else args.persona
    print(f"=== adversarial run: persona={persona} ===")
    run(persona)
    return 0


if __name__ == "__main__":
    sys.exit(main())
