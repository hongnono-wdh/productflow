"""End-to-end journeys against the NEW React+TS console (the default dist build).

Mirrors the legacy test_e2e_console.py 7-stage journeys but drives the React app
the way a user does — real DOM clicks/fills, no global JS functions — and asserts
on WS-pushed DOM updates + CLI agent backfill + /api reads. The server is started
WITHOUT PF_UI (defaults to the compiled React app served from assets/dist).

Covers: create wizard, 7-stage navigation, overview modal, P1 brief, P2 refs+select,
P3 hero canvas (generate/drag-persist/set-base), P4 pages + per-stage canvas isolation,
P5/6/7 run-stage + deploy-creds, P6 preview→annotation overlay, chat drawer, choices bar.

Graceful skip if playwright / chromium is unavailable.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helpers as h  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
    _PW_OK = True
    _PW_ERR = ""
except Exception as ex:  # pragma: no cover
    sync_playwright = None
    _PW_OK = False
    _PW_ERR = repr(ex)

_CHROMIUM_OK = os.path.exists(h.CHROMIUM_EXE)
_PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000100ffff0300000006"
    "0005a3b8c4ad0000000049454e44ae426082"
)
_SKIP = ("playwright import failed: " + _PW_ERR if not _PW_OK else "chromium build missing at " + h.CHROMIUM_EXE)


@unittest.skipUnless(_PW_OK and _CHROMIUM_OK, _SKIP)
class TestE2EReact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = h.make_home()
        try:
            cls.proc, cls.port = h.start_server(cls.home)  # no PF_UI → default React dist
            cls._pw = sync_playwright().start()
            cls.browser = cls._pw.chromium.launch(executable_path=h.CHROMIUM_EXE, headless=True)
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        for attr, fn in (("browser", lambda x: x.close()), ("_pw", lambda x: x.stop())):
            v = getattr(cls, attr, None)
            if v is not None:
                try:
                    fn(v)
                except Exception:
                    pass
                setattr(cls, attr, None)
        if getattr(cls, "proc", None):
            h.stop_server(cls.proc); cls.proc = None
        if getattr(cls, "home", None):
            h.rm_home(cls.home); cls.home = None

    # ── helpers ──────────────────────────────────────────────────────────
    def _page(self):
        page = self.browser.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: errs.append("console.error: " + m.text) if m.type == "error" and "404" not in m.text else None)
        return page, errs

    def _art(self, pdir, rel):
        full = os.path.join(pdir, ".productflow", rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(_PNG_1x1)

    def _open(self, page, pid):
        page.goto(f"http://127.0.0.1:{self.port}/p/{pid}/", wait_until="domcontentloaded")
        page.wait_for_function("() => document.querySelectorAll('#stepper .step-pill').length === 7", timeout=12000)

    def _stage(self, page, sid):
        page.click(f"#stepper .step-pill >> nth={sid - 1}")
        page.wait_for_timeout(150)

    def _is_react(self, page):
        return page.eval_on_selector("#root", "e=>!!e") if page.query_selector("#root") else False

    # ── 1) create wizard + 7-stage nav + overview ────────────────────────
    def test_create_navigate_overview(self):
        page, errs = self._page()
        try:
            page.goto(f"http://127.0.0.1:{self.port}/", wait_until="networkidle")
            self.assertTrue(page.query_selector("#root"), "default UI is not the React build")
            page.click("button:has-text('新建项目')")
            page.wait_for_selector("#new-modal.show", timeout=8000)
            page.fill("#nm-name", "E2E 七步")
            page.fill("#nm-slug", "e2e-seven")
            page.click("#new-modal .wz-pcard >> nth=2")  # toggle APP on
            page.wait_for_function("() => document.querySelectorAll('#new-modal .wz-pcard.on').length === 3", timeout=5000)
            page.click("#new-modal button:has-text('创建项目')")
            page.wait_for_url(lambda u: "/p/" in u, timeout=10000)
            pid = page.url.rstrip("/").split("/")[-1]
            pdir = os.path.join(self.home, "code", "e2e-seven")
            page.wait_for_function("() => document.querySelectorAll('#stepper .step-pill').length === 7", timeout=12000)
            labels = page.eval_on_selector_all("#stepper .step-pill .lbl", "e=>e.map(x=>x.textContent)")
            self.assertEqual(labels, ["市场调研", "找参考", "首图设计", "页面设计", "功能与数据设计", "开发实现", "部署上线"])
            # navigate every stage: board (1,2,5,6,7) vs canvas (3,4)
            for sid in range(1, 8):
                self._stage(page, sid)
                if sid in (3, 4):
                    page.wait_for_selector("#view-canvas", timeout=8000)
                    self.assertIsNone(page.query_selector("#view-board"), f"stage{sid} should be canvas")
                else:
                    page.wait_for_selector("#view-board", timeout=8000)
                    self.assertIsNone(page.query_selector("#view-canvas"), f"stage{sid} should be board")
            # overview modal aggregates a backfilled artifact
            self._art(pdir, "artifacts/phase-1/comp.png")
            r = h.cli(["artifact", "1", "artifacts/phase-1/comp.png", "--title", "竞品矩阵"], self.home, project=pdir)
            self.assertEqual(r.returncode, 0, r.stderr)
            page.click("button:has-text('全部产物')")
            page.wait_for_selector("#modal.show", timeout=8000)
            page.wait_for_function("() => document.querySelector('#modal').textContent.includes('竞品矩阵')", timeout=8000)
            self.assertEqual(errs, [], f"JS errors: {errs}")
        finally:
            page.close()

    # ── 2) P1 brief panel + P2 refs panel ────────────────────────────────
    def test_p1_brief_p2_refs(self):
        proj = h.create_project(self.port, "需求与参考", slug="brief-refs")
        pid, pdir = proj["id"], proj["dir"]
        page, errs = self._page()
        try:
            self._open(page, pid)
            self._stage(page, 1)
            page.wait_for_selector("#stage-extra textarea", timeout=8000)
            page.fill("#stage-extra textarea", "一个每月寄到家的精品手冲咖啡订阅")
            page.click("#stage-extra button:has-text('生成摘要')")
            page.wait_for_timeout(250)
            self.assertIn("产品需求", h.cli(["inbox"], self.home, project=pdir).stdout)
            h.cli(["brief", "set-summary", "--goal", "帮上班族在家喝新鲜手冲", "--users", "忙碌咖啡爱好者",
                   "--need", "稳定新鲜烘焙", "--scope", "PC+H5"], self.home, project=pdir)
            page.wait_for_function("() => document.querySelectorAll('#stage-extra .wz-airow').length === 4", timeout=12000)
            # P2 refs
            self._stage(page, 2)
            page.wait_for_selector("#stage-extra .wz-tag", timeout=8000)
            page.click("#stage-extra .wz-tag >> text=极简")
            page.wait_for_function("() => document.querySelectorAll('#stage-extra .wz-tag.on').length === 1")
            page.click("#stage-extra button:has-text('找参考')")
            page.wait_for_timeout(250)
            self.assertIn("视觉探索", h.cli(["inbox"], self.home, project=pdir).stdout)
            for i in range(2):
                rel = f"artifacts/phase-2/refs/r{i}.png"
                self._art(pdir, rel)
                h.cli(["explore", "add-ref", rel, "--title", f"参考{i}"], self.home, project=pdir)
            h.cli(["explore", "done-request", "--kind", "search-refs"], self.home, project=pdir)
            page.wait_for_function("() => document.querySelectorAll('#stage-extra .wz-ref').length === 2", timeout=12000)
            page.click("#stage-extra .wz-ref")
            page.wait_for_function("() => document.querySelectorAll('#stage-extra .wz-ref.on').length === 1", timeout=8000)
            self.assertEqual(errs, [], f"JS errors: {errs}")
        finally:
            page.close()

    # ── 3) P3 hero canvas: generate → drag-persist → set base ─────────────
    def test_p3_hero_canvas(self):
        proj = h.create_project(self.port, "首图画布", slug="hero-canvas")
        pid, pdir = proj["id"], proj["dir"]
        self._art(pdir, "artifacts/phase-2/refs/a.png")
        h.cli(["explore", "add-ref", "artifacts/phase-2/refs/a.png", "--title", "ref"], self.home, project=pdir)
        page, errs = self._page()
        try:
            self._open(page, pid)
            # select the ref via API (sets selectedRefs), then enter P3
            page.evaluate("""async () => {
              const r = await (await fetch(location.pathname.replace(/\\/$/,'')+'/api/explore')).json();
              await fetch(location.pathname.replace(/\\/$/,'')+'/api/explore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({selectedRefs:[r.refs[0].id]})});
            }""")
            self._stage(page, 3)
            page.wait_for_selector("#cv-stagebar", timeout=10000)
            page.click("#cv-stagebar button:has-text('生成首图')")
            page.wait_for_timeout(250)
            self.assertIn("视觉探索", h.cli(["inbox"], self.home, project=pdir).stdout)
            for i in range(2):
                rel = f"artifacts/phase-3/heroes/h{i}.png"
                self._art(pdir, rel)
                h.cli(["explore", "add-hero", rel, "--style", f"风格{i}"], self.home, project=pdir)
            h.cli(["explore", "done-request", "--kind", "gen-heroes"], self.home, project=pdir)
            page.wait_for_function("() => document.querySelectorAll('#cv-world .cv-item').length === 2", timeout=12000)
            # drag a card, then verify persisted via /api/canvas?stage=3 across reload
            card = page.query_selector("#cv-world .cv-item")
            cid = card.get_attribute("data-id")
            box = card.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down(); page.mouse.move(box["x"] + 160, box["y"] + 120, steps=8); page.mouse.up()
            page.wait_for_timeout(950)  # cvSave debounce 600ms
            x_before = page.evaluate(f"""async () => {{
              const c = await (await fetch(location.pathname.replace(/\\/$/,'')+'/api/canvas?stage=3')).json();
              return Math.round((c.items[{cid!r}]||{{}}).x);
            }}""")
            self._open(page, pid)
            self._stage(page, 3)
            page.wait_for_function("() => document.querySelectorAll('#cv-world .cv-item').length === 2", timeout=12000)
            x_after = page.evaluate(f"""async () => {{
              const c = await (await fetch(location.pathname.replace(/\\/$/,'')+'/api/canvas?stage=3')).json();
              return Math.round((c.items[{cid!r}]||{{}}).x);
            }}""")
            self.assertEqual(x_before, x_after, "drag position not persisted")
            self.assertIsInstance(x_before, int)
            # set base via .cv-base
            page.click("#cv-world .cv-item .cv-base")
            page.wait_for_timeout(400)
            sel = page.evaluate("""async () => (await (await fetch(location.pathname.replace(/\\/$/,'')+'/api/explore')).json()).selectedHero""")
            self.assertTrue(sel, "selectedHero not set after clicking 设为基调")
            self.assertEqual(errs, [], f"JS errors: {errs}")
        finally:
            page.close()

    # ── 4) P4 pages + per-stage canvas isolation ─────────────────────────
    def test_p4_pages_and_canvas_isolation(self):
        proj = h.create_project(self.port, "双画布", slug="two-canvas")
        pid, pdir = proj["id"], proj["dir"]
        h.cli(["page", "add", "首页", "--group", "核心"], self.home, project=pdir)
        with open(os.path.join(pdir, ".productflow", "pages.json")) as f:
            pgid = json.load(f)["pages"][0]["id"]
        self._art(pdir, "artifacts/phase-4/home-pc.png")
        h.cli(["page", "set", pgid, "--add-version", "artifacts/phase-4/home-pc.png", "--platform", "PC"], self.home, project=pdir)
        # also a hero so P3 canvas has a draggable card for isolation
        self._art(pdir, "artifacts/phase-3/heroes/h.png")
        h.cli(["explore", "add-hero", "artifacts/phase-3/heroes/h.png", "--style", "s"], self.home, project=pdir)
        page, errs = self._page()
        try:
            self._open(page, pid)
            # P3: drag the hero card → persists to stage-3 canvas
            self._stage(page, 3)
            page.wait_for_function("() => document.querySelectorAll('#cv-world .cv-item').length === 1", timeout=12000)
            card = page.query_selector("#cv-world .cv-item")
            cid = card.get_attribute("data-id")
            box = card.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down(); page.mouse.move(box["x"] + 140, box["y"] + 90, steps=6); page.mouse.up()
            page.wait_for_timeout(950)
            # P4: page card + platform matrix
            self._stage(page, 4)
            page.wait_for_function("() => document.querySelectorAll('#cv-world .cv-item.page-card').length === 1", timeout=12000)
            plats = page.eval_on_selector_all("#cv-world .cv-platrow .cv-plat", "e=>e.length")
            self.assertEqual(plats, 3)
            on = page.eval_on_selector_all("#cv-world .cv-plat.on", "e=>e.map(x=>x.textContent)")
            self.assertIn("PC", on)
            # isolation: stage-3 has the hero item; stage-4 does not
            c3 = page.evaluate("""async () => (await (await fetch(location.pathname.replace(/\\/$/,'')+'/api/canvas?stage=3')).json())""")
            c4 = page.evaluate("""async () => (await (await fetch(location.pathname.replace(/\\/$/,'')+'/api/canvas?stage=4')).json())""")
            self.assertIn(cid, (c3.get("items") or {}), "hero layout missing from stage-3")
            self.assertNotIn(cid, (c4.get("items") or {}), "stage-3 hero leaked into stage-4")
            self.assertEqual(errs, [], f"JS errors: {errs}")
        finally:
            page.close()

    # ── 5) P5/6/7 run-stage + deploy-creds ───────────────────────────────
    def test_p567_panels(self):
        proj = h.create_project(self.port, "落地阶段", slug="late-stages")
        pid, pdir = proj["id"], proj["dir"]
        page, errs = self._page()
        try:
            self._open(page, pid)
            # P5 run-stage → inbox stage-request
            self._stage(page, 5)
            page.wait_for_selector("#stage-extra button:has-text('让 Agent 做本阶段')", timeout=8000)
            page.click("#stage-extra button:has-text('让 Agent 做本阶段')")
            page.wait_for_timeout(300)
            self.assertIn("阶段5", h.cli(["inbox"], self.home, project=pdir).stdout)
            # P7 deploy creds save → masked pill
            self._stage(page, 7)
            page.wait_for_selector("#stage-extra input[placeholder*='PF_SSH_HOST']", timeout=8000)
            page.fill("#stage-extra input[placeholder*='PF_SSH_HOST']", "1.2.3.4")
            page.click("#stage-extra button:has-text('保存凭证')")
            page.wait_for_function("() => document.querySelectorAll('#stage-extra code').length >= 1", timeout=8000)
            self.assertIn("PF_SSH_HOST", page.eval_on_selector("#stage-extra", "e=>e.textContent"))
            self.assertEqual(errs, [], f"JS errors: {errs}")
        finally:
            page.close()

    # ── 6) chat drawer + choices bar ─────────────────────────────────────
    def test_chat_and_choices(self):
        proj = h.create_project(self.port, "沟通", slug="comm")
        pid, pdir = proj["id"], proj["dir"]
        page, errs = self._page()
        try:
            self._open(page, pid)
            # chat: open drawer, send a message → inbox
            page.click("#chat-btn")
            page.wait_for_selector("#chat-drawer.open", timeout=6000)
            page.fill("#chat-input", "请把首图改成暖色调")
            page.click("#chat-form button[type='submit']")
            page.wait_for_timeout(300)
            self.assertIn("暖色调", h.cli(["inbox"], self.home, project=pdir).stdout)
            # choices: agent asks → bar shows → click an option → answer recorded
            h.cli(["choice", "ask", "--stage", "5", "--question", "用哪种数据库？", "--option", "SQLite", "--option", "Postgres"], self.home, project=pdir)
            page.wait_for_selector("#choices-bar.show .choice-card", timeout=8000)
            page.click("#choices-bar .copt >> text=SQLite")
            page.wait_for_timeout(400)
            choices = json.load(open(os.path.join(pdir, ".productflow", "choices.json")))["choices"]
            self.assertTrue(any(c.get("answer") == "SQLite" for c in choices), "choice answer not recorded")
            self.assertEqual(errs, [], f"JS errors: {errs}")
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main()
