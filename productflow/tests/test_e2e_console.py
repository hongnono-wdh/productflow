"""End-to-end console journey driven by a real (headless) browser.

Uses the python-playwright *sync* API to drive assets/console.html as a human
would, for the 7-stage model: create a project via the minimal #new-modal
(name + platform), then work *inside the project* stage by stage —
①市场调研(产品需求面板) ②找参考(面板) ③首图设计(画布) ④页面设计(画布) ⑤功能 ⑥开发
⑦部署 — backfilling agent results from the CLI side (cli()) at each checkpoint,
mirroring the real "browser drives the front end, CLI agent fills results" loop.

Isolation rides entirely on helpers: a throwaway HOME sandboxes ~/.productflow
and ~/code, the server runs on a free port in that sandbox, and a no-op `claude`
stub keeps the server's auto-spawn from launching real agents.

Graceful degradation: if python-playwright can't be imported or the pinned
chromium build is absent, the whole TestCase is skipped instead of failing.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helpers as h  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
    _PW_OK = True
    _PW_ERR = ""
except Exception as ex:  # pragma: no cover - import-time only
    sync_playwright = None
    _PW_OK = False
    _PW_ERR = repr(ex)

_CHROMIUM_OK = os.path.exists(h.CHROMIUM_EXE)

# A 1x1 transparent PNG — written to disk so thumbnails resolve to a real image.
_PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000100ffff0300000006"
    "0005a3b8c4ad0000000049454e44ae426082"
)

_SKIP_REASON = (
    "playwright import failed: " + _PW_ERR if not _PW_OK
    else "chromium build missing at " + h.CHROMIUM_EXE
)


@unittest.skipUnless(_PW_OK and _CHROMIUM_OK, _SKIP_REASON)
class TestE2EConsole(unittest.TestCase):
    home = None
    proc = None
    port = None
    _pw = None
    browser = None

    @classmethod
    def setUpClass(cls):
        cls.home = h.make_home()
        try:
            cls.proc, cls.port = h.start_server(cls.home)
            cls._pw = sync_playwright().start()
            cls.browser = cls._pw.chromium.launch(
                executable_path=h.CHROMIUM_EXE, headless=True,
            )
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        if cls.browser is not None:
            try:
                cls.browser.close()
            except Exception:
                pass
            cls.browser = None
        if cls._pw is not None:
            try:
                cls._pw.stop()
            except Exception:
                pass
            cls._pw = None
        if cls.proc is not None:
            h.stop_server(cls.proc)
            cls.proc = None
        if cls.home is not None:
            h.rm_home(cls.home)
            cls.home = None

    # ── helpers ───────────────────────────────────────────────────────────
    def _new_page(self):
        page = self.browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        return page, errors

    def _write_artifact(self, project_dir, rel):
        full = os.path.join(project_dir, ".productflow", rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(_PNG_1x1)

    def _open_project(self, page, pid):
        page.goto(f"http://127.0.0.1:{self.port}/p/{pid}/", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('#stepper .step-pill').length === 7",
            timeout=12000)

    # ── creation modal + 7-stage navigation + overview ─────────────────────
    def test_create_modal_navigate_overview(self):
        page, errors = self._new_page()
        try:
            page.goto(f"http://127.0.0.1:{self.port}/", wait_until="domcontentloaded")
            page.wait_for_function("() => typeof openNewModal === 'function'", timeout=10000)
            # 极简创建：名称 + slug + 切 APP 平台
            page.evaluate("openNewModal()")
            page.wait_for_selector("#new-modal.show", timeout=8000)
            page.fill("#nm-name", "E2E 七步")
            page.fill("#nm-slug", "e2e-seven")
            page.click("#new-body .wz-pcard[data-plat='APP']")
            page.wait_for_function(
                "() => document.querySelectorAll('#new-body .wz-pcard.on').length === 3", timeout=5000)
            page.evaluate("createProject()")
            page.wait_for_url(lambda u: "/p/" in u, timeout=10000)
            pid = page.url.rstrip("/").split("/")[-1]
            project_dir = os.path.join(self.home, "code", "e2e-seven")
            page.wait_for_function(
                "() => document.querySelectorAll('#stepper .step-pill').length === 7", timeout=12000)
            labels = page.eval_on_selector_all("#stepper .step-pill .lbl", "e=>e.map(x=>x.textContent)")
            self.assertEqual(labels, ["市场调研", "找参考", "首图设计", "页面设计",
                                      "功能与数据设计", "开发实现", "部署上线"])
            # 逐个阶段：面板(1,2,5,6,7) vs 画布(3,4)
            for sid in range(1, 8):
                page.evaluate(f"selectStage({sid})")
                page.wait_for_timeout(120)
                board = page.eval_on_selector("#view-board", "e=>getComputedStyle(e).display")
                canvas = page.eval_on_selector("#view-canvas", "e=>getComputedStyle(e).display")
                if sid in (3, 4):
                    self.assertNotEqual(canvas, "none", f"阶段{sid}应是画布")
                else:
                    self.assertNotEqual(board, "none", f"阶段{sid}应是面板")
            # 全部产物总览：先登记一个产物，再打开
            self._write_artifact(project_dir, "artifacts/phase-1/comp.png")
            r = h.cli(["artifact", "1", "artifacts/phase-1/comp.png", "--title", "竞品矩阵"],
                      self.home, project=project_dir)
            self.assertEqual(r.returncode, 0, r.stderr)
            # 等前端 state 轮询到这个新产物，再开总览
            page.wait_for_function(
                "() => state && state.phases && (state.phases[0].artifacts||[]).length > 0", timeout=8000)
            page.evaluate("openOverview()")
            page.wait_for_function(
                "() => { const m=document.getElementById('modal'); return m && m.classList.contains('show'); }",
                timeout=8000)
            self.assertIn("竞品矩阵", page.eval_on_selector("#modal", "e=>e.textContent"))
            self.assertEqual(errors, [], f"JS 错误: {errors}")
        finally:
            page.close()

    # ── P1 产品需求面板 + P2 找参考面板 ────────────────────────────────────
    def test_p1_brief_and_p2_refs(self):
        proj = h.create_project(self.port, "需求与参考", slug="brief-refs")
        pid, pdir = proj["id"], proj["dir"]
        page, errors = self._new_page()
        try:
            self._open_project(page, pid)
            # P1 产品需求
            page.evaluate("selectStage(1)")
            page.wait_for_selector("#st-brief", timeout=8000)
            page.fill("#st-brief", "一个每月寄到家的精品手冲咖啡订阅")
            # 点真实按钮（会让描述框失焦）——模拟真实操作；轮询在输入框聚焦时不重渲染以保护中文输入
            page.click("#stage-extra button:has-text('生成摘要')")
            page.wait_for_timeout(200)
            self.assertIn("产品需求", h.cli(["inbox"], self.home, project=pdir).stdout)
            h.cli(["brief", "set-summary", "--goal", "帮上班族在家喝新鲜手冲",
                   "--users", "忙碌咖啡爱好者", "--need", "稳定新鲜烘焙", "--scope", "PC+H5"],
                  self.home, project=pdir)
            page.wait_for_function(
                "() => document.querySelectorAll('#stage-extra .wz-airow').length === 4", timeout=12000)
            # P2 找参考
            page.evaluate("selectStage(2)")
            page.wait_for_selector("#stage-extra .wz-tag", timeout=8000)
            page.click("#stage-extra .wz-tag[data-tag='极简']")
            page.wait_for_function("()=>document.querySelectorAll('#stage-extra .wz-tag.on').length===1")
            page.evaluate("searchRefs()")
            page.wait_for_timeout(200)
            self.assertIn("视觉探索", h.cli(["inbox"], self.home, project=pdir).stdout)
            for i in range(2):
                rel = f"artifacts/phase-2/refs/r{i}.png"
                self._write_artifact(pdir, rel)
                h.cli(["explore", "add-ref", rel, "--title", f"参考{i}"], self.home, project=pdir)
            h.cli(["explore", "done-request", "--kind", "search-refs"], self.home, project=pdir)
            page.wait_for_function(
                "() => document.querySelectorAll('#stage-extra .wz-ref').length === 2", timeout=12000)
            page.click("#stage-extra .wz-ref")
            page.wait_for_function(
                "() => document.querySelectorAll('#stage-extra .wz-ref.on').length === 1", timeout=8000)
            self.assertEqual(errors, [], f"JS 错误: {errors}")
        finally:
            page.close()

    # ── P3 首图画布：生成 → 铺画布 → 拖拽持久化 → 设为基调 ──────────────────
    def test_p3_hero_canvas(self):
        proj = h.create_project(self.port, "首图画布", slug="hero-canvas")
        pid, pdir = proj["id"], proj["dir"]
        # 预置一张选中的参考（首图依赖 selectedRefs）
        self._write_artifact(pdir, "artifacts/phase-2/refs/a.png")
        h.cli(["explore", "add-ref", "artifacts/phase-2/refs/a.png", "--title", "ref"],
              self.home, project=pdir)
        page, errors = self._new_page()
        try:
            self._open_project(page, pid)
            # 选中该参考（设 selectedRefs）
            page.evaluate("""async () => {
              const r = await (await fetch(PF_BASE+'/api/explore')).json();
              const id = r.refs[0].id;
              await fetch(PF_BASE+'/api/explore',{method:'POST',headers:{'Content-Type':'application/json'},
                body: JSON.stringify({selectedRefs:[id]})});
            }""")
            page.evaluate("selectStage(3)")
            page.wait_for_function("() => cvStage === 3 && cvLoaded", timeout=10000)
            # 生成首图（用 selectedRefs）
            page.wait_for_function("() => (pExplore.selectedRefs||[]).length === 1", timeout=8000)
            page.evaluate("genHeroes()")
            page.wait_for_timeout(200)
            self.assertIn("视觉探索", h.cli(["inbox"], self.home, project=pdir).stdout)
            for i in range(2):
                rel = f"artifacts/phase-3/heroes/h{i}.png"
                self._write_artifact(pdir, rel)
                h.cli(["explore", "add-hero", rel, "--style", f"风格{i}"], self.home, project=pdir)
            h.cli(["explore", "done-request", "--kind", "gen-heroes"], self.home, project=pdir)
            # 两张首图卡片铺到画布
            page.wait_for_function(
                "() => document.querySelectorAll('#cv-world .cv-item').length === 2", timeout=12000)
            # 拖一张 → 记录坐标 → reload → 坐标保留（per-stage 持久化）
            card = page.query_selector("#cv-world .cv-item")
            box = card.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down(); page.mouse.move(box["x"] + 160, box["y"] + 120, steps=8); page.mouse.up()
            page.wait_for_timeout(900)  # 让 cvSave debounce(600ms) 落盘
            cid = card.get_attribute("data-id")
            x_before = page.evaluate(f"() => Math.round(cv.items[{cid!r}].x)")
            # reload
            self._open_project(page, pid)
            page.evaluate("selectStage(3)")
            page.wait_for_function("() => cvStage === 3 && cvLoaded", timeout=10000)
            page.wait_for_function(
                "() => document.querySelectorAll('#cv-world .cv-item').length === 2", timeout=12000)
            x_after = page.evaluate(f"() => Math.round((cv.items[{cid!r}]||{{}}).x)")
            self.assertEqual(x_before, x_after, "拖拽坐标未持久化")
            # 设为基调
            hero_file = page.evaluate("""async () => {
              const r = await (await fetch(PF_BASE+'/api/explore')).json(); return r.heroes[0].file;
            }""")
            page.evaluate(f"setHeroBase({hero_file!r})")
            page.wait_for_timeout(400)
            sel = page.evaluate("""async () => (await (await fetch(PF_BASE+'/api/explore')).json()).selectedHero""")
            self.assertEqual(sel, hero_file)
            self.assertEqual(errors, [], f"JS 错误: {errors}")
        finally:
            page.close()

    # ── P3/P4 两块画布互不串 + P4 页面×平台 ────────────────────────────────
    def test_canvas_isolation_and_p4_pages(self):
        proj = h.create_project(self.port, "双画布", slug="two-canvas")
        pid, pdir = proj["id"], proj["dir"]
        # 一个页面 + PC 版本
        r = h.cli(["page", "add", "首页", "--group", "核心"], self.home, project=pdir)
        self.assertEqual(r.returncode, 0, r.stderr)
        self._write_artifact(pdir, "artifacts/phase-4/home-pc.png")
        pgid = None
        import json
        with open(os.path.join(pdir, ".productflow", "pages.json")) as f:
            pages = json.load(f)["pages"]
        pgid = pages[0]["id"]
        h.cli(["page", "set", pgid, "--add-version", "artifacts/phase-4/home-pc.png", "--platform", "PC"],
              self.home, project=pdir)
        page, errors = self._new_page()
        try:
            self._open_project(page, pid)
            # 在 P3 画布留一份布局
            page.evaluate("selectStage(3)")
            page.wait_for_function("() => cvStage === 3 && cvLoaded", timeout=10000)
            page.evaluate("""() => { cv.notes.push({id:'n_iso', x:11, y:22, text:'p3'}); cvSave(); }""")
            page.wait_for_timeout(900)
            # 切到 P4 页面画布
            page.evaluate("selectStage(4)")
            page.wait_for_function("() => cvStage === 4 && cvLoaded", timeout=10000)
            page.wait_for_function(
                "() => document.querySelectorAll('#cv-world .cv-page, #cv-world .cv-item').length >= 1",
                timeout=12000)
            # 后端两 stage 各自独立
            c3 = page.evaluate("""async () => (await (await fetch(PF_BASE+'/api/canvas?stage=3')).json())""")
            c4 = page.evaluate("""async () => (await (await fetch(PF_BASE+'/api/canvas?stage=4')).json())""")
            self.assertTrue(any(n.get("id") == "n_iso" for n in (c3.get("notes") or [])),
                            "P3 便签应在 stage=3")
            self.assertFalse(any(n.get("id") == "n_iso" for n in (c4.get("notes") or [])),
                             "P3 便签不该串到 stage=4")
            # 切回 P3，布局还在
            page.evaluate("selectStage(3)")
            page.wait_for_function("() => cvStage === 3 && cvLoaded", timeout=10000)
            keep = page.evaluate("""() => (cv.notes||[]).some(n=>n.id==='n_iso')""")
            self.assertTrue(keep, "切回 P3 后布局被覆盖")
            self.assertEqual(errors, [], f"JS 错误: {errors}")
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main()
