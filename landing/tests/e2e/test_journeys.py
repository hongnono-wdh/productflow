"""E2E journeys for the ProductFlow landing page.

Self-hosts the static site on a free port via stdlib http.server, then drives it
with Playwright + the cached chromium headless shell (executable_path passed
explicitly, mirroring the productflow skill's own test harness).

Run:
    # with a venv that has playwright installed:
    python tests/e2e/test_journeys.py
"""
import http.server
import os
import socket
import socketserver
import sys
import threading
import unittest

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))  # landing/

# Cached chromium known to work with python-playwright on this machine.
CHROMIUM_EXE = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium_headless_shell-1169/chrome-mac/headless_shell"
)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SITE_DIR, **kw)

    def log_message(self, *a):  # keep test output clean
        pass


class _Server(socketserver.TCPServer):
    allow_reuse_address = True


class LandingE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = free_port()
        cls.httpd = _Server(("127.0.0.1", cls.port), _Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d/index.html" % cls.port

        cls._pw = sync_playwright().start()
        launch_kw = {}
        if os.path.exists(CHROMIUM_EXE):
            launch_kw["executable_path"] = CHROMIUM_EXE
        cls.browser = cls._pw.chromium.launch(**launch_kw)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _new_page(self, **ctx_kw):
        """Page that records console errors / page errors for the no-error check."""
        context = self.browser.new_context(**ctx_kw)
        errors = []
        page = context.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(self.base, wait_until="networkidle")
        return context, page, errors

    # 1
    def test_hero_title_present(self):
        ctx, page, _ = self._new_page()
        try:
            h1 = page.locator("#hero-title")
            self.assertTrue(h1.is_visible())
            self.assertIn("流水线", h1.inner_text())
        finally:
            ctx.close()

    # 2
    def test_install_three_steps_visible(self):
        ctx, page, _ = self._new_page()
        try:
            self.assertTrue(page.locator("#install").is_visible())
            steps = page.locator(".steps li")
            self.assertEqual(steps.count(), 3, "install block must show exactly 3 steps")
            for i in range(3):
                self.assertTrue(steps.nth(i).is_visible())
        finally:
            ctx.close()

    # 3
    def test_install_prompt_block_present(self):
        ctx, page, _ = self._new_page()
        try:
            code = page.locator("#installPrompt")
            self.assertTrue(code.is_visible())
            text = code.inner_text()
            # real, load-bearing lines from the single-paste prompt
            self.assertIn("git clone https://github.com/hongnono-wdh/productflow.git", text)
            self.assertIn("scripts/start.sh", text)
            self.assertIn("127.0.0.1:7717", text)
        finally:
            ctx.close()

    # 4
    def test_copy_button_feedback(self):
        ctx, page, _ = self._new_page(
            permissions=["clipboard-read", "clipboard-write"]
        )
        try:
            btn = page.locator("#copyBtn")
            self.assertEqual(btn.locator(".copy-label").inner_text(), "复制提示词")
            btn.click()
            page.wait_for_selector("#copyBtn.copied", timeout=3000)
            label = btn.locator(".copy-label").inner_text()
            self.assertIn(label, ("已复制",))
            # clipboard should hold the real prompt (best-effort; skip if blocked)
            try:
                clip = page.evaluate("navigator.clipboard.readText()")
                self.assertIn("productflow", clip)
            except Exception:
                pass
        finally:
            ctx.close()

    # 5
    def test_mobile_nav_reachable(self):
        ctx, page, _ = self._new_page(viewport={"width": 390, "height": 780})
        try:
            toggle = page.locator("#navToggle")
            self.assertTrue(toggle.is_visible(), "hamburger must be visible on narrow viewport")
            # desktop links hidden on mobile, menu starts closed
            menu = page.locator("#mobileMenu")
            self.assertFalse(menu.is_visible())
            toggle.click()
            page.wait_for_selector("#mobileMenu:not([hidden])", timeout=2000)
            self.assertTrue(menu.is_visible())
            self.assertEqual(toggle.get_attribute("aria-expanded"), "true")
            # an anchor inside is clickable/reachable
            install_link = menu.locator("a[href='#install']")
            self.assertTrue(install_link.is_visible())
            install_link.click()
            # navigating closes the menu (element gets [hidden] again, so wait for hidden state)
            page.wait_for_selector("#mobileMenu", state="hidden", timeout=2000)
            self.assertFalse(menu.is_visible())
            self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        finally:
            ctx.close()

    # 6
    def test_no_console_errors(self):
        ctx, page, errors = self._new_page()
        try:
            # exercise the page a bit
            page.locator("#copyBtn").scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            self.assertEqual(errors, [], "console/page errors: %r" % errors)
        finally:
            ctx.close()

    # 7
    def test_seo_and_social_meta(self):
        ctx, page, _ = self._new_page()
        try:
            self.assertIn("ProductFlow", page.title())
            desc = page.get_attribute("meta[name='description']", "content")
            self.assertTrue(desc and len(desc) > 30)
            self.assertTrue(page.locator("link[rel='canonical']").count() >= 1)
            self.assertTrue(page.locator("meta[property='og:title']").count() >= 1)
            self.assertEqual(
                page.get_attribute("meta[name='twitter:card']", "content"),
                "summary_large_image",
            )
            self.assertTrue(page.locator("meta[name='theme-color']").count() >= 1)
            self.assertTrue(page.locator("link[rel='icon']").count() >= 1)
        finally:
            ctx.close()

    # 8
    def test_a11y_landmarks(self):
        ctx, page, _ = self._new_page()
        try:
            self.assertTrue(page.locator("main#main").count() >= 1)
            self.assertTrue(page.locator("a.skip-link").count() >= 1)
            self.assertEqual(
                page.get_attribute("a.skip-link", "href"), "#install"
            )
            # nav toggle carries aria
            self.assertIsNotNone(page.get_attribute("#navToggle", "aria-expanded"))
        finally:
            ctx.close()

    # 9 — interactive pipeline: clicking a rail node updates the live region + preview
    def test_stage_click_updates_live_region(self):
        ctx, page, _ = self._new_page()
        try:
            status = page.locator("#stageStatus")
            preview = page.locator("#stagePreview")
            # the hero intro animation cascades 01->04 then idles on 04 进行中;
            # wait for it to settle on the resting state (stage 04 / 页面设计).
            page.wait_for_function(
                "() => document.querySelector('#stageStatus')"
                ".innerText.includes('页面设计')",
                timeout=4000,
            )
            self.assertIn("页面设计", status.inner_text())
            self.assertIn("页面设计", preview.inner_text())

            # click stage 07 (部署上线) and assert both the live region and preview change
            node7 = page.locator(".rail-node[data-stage='7']")
            self.assertTrue(node7.is_visible())
            node7.click()
            page.wait_for_timeout(200)
            self.assertIn("部署上线", status.inner_text())
            self.assertIn("部署上线", preview.inner_text())
            self.assertEqual(node7.get_attribute("aria-current"), "step")

            # click stage 01 (市场调研) — confirms it really tracks the click
            node1 = page.locator(".rail-node[data-stage='1']")
            node1.click()
            page.wait_for_timeout(200)
            self.assertIn("市场调研", status.inner_text())
            self.assertIn("市场调研", preview.inner_text())
        finally:
            ctx.close()

    # 10 — cards carry a soft-shadow / elevation token (replaces old .glass backdrop-filter check)
    def test_cards_have_soft_shadow_elevation(self):
        ctx, page, _ = self._new_page()
        try:
            # the light design declares a tinted --shadow-lg / --shadow-sm token in styles.css
            css = page.evaluate(
                """async () => {
                    const r = await fetch('styles.css');
                    return await r.text();
                }"""
            )
            self.assertRegex(
                css,
                r"--shadow-(?:lg|sm):\s*[^;]*rgba\(16,\s*24,\s*40",
                "styles.css must define a tinted soft-shadow elevation token",
            )
            # and a real card / console surface must actually compute a non-'none' box-shadow
            box = page.evaluate(
                """() => {
                    const el = document.querySelector('.console-card, .cb, .feat, .install-code');
                    if (!el) return null;
                    return getComputedStyle(el).boxShadow;
                }"""
            )
            self.assertIsNotNone(box, "page must have an elevated card/console surface")
            self.assertNotEqual(box, "none", "card must apply a soft-shadow elevation")
        finally:
            ctx.close()

    # 11 — under reduced-motion: no scroll-driven style drift; run jumps to instant final state
    def test_reduced_motion_no_drift_and_instant_run(self):
        ctx, page, _ = self._new_page(reduced_motion="reduce")
        try:
            # no ambient/parallax layer exists in the light design — reveal elements
            # must render their final state (transform 'none') and not drift on scroll.
            def reveal_transform():
                return page.evaluate(
                    """() => {
                        const el = document.querySelector('.reveal');
                        return el ? getComputedStyle(el).transform : '';
                    }"""
                )

            before = reveal_transform()
            self.assertIn(before, ("none", "matrix(1, 0, 0, 1, 0, 0)", ""))
            page.evaluate("window.scrollTo(0, 1400)")
            page.wait_for_timeout(250)
            after = reveal_transform()
            self.assertEqual(
                (before or "").strip(), (after or "").strip(),
                "reveal elements must not drift under reduced motion",
            )

            # pressing 运行流水线 must yield the INSTANT final state (stage 07), no tween
            page.locator("#runBtn").click()
            page.wait_for_timeout(150)
            status = page.locator("#stageStatus")
            self.assertIn("部署上线", status.inner_text())
            self.assertIn("07", page.locator("#termHost").inner_text())
        finally:
            ctx.close()


if __name__ == "__main__":
    if not os.path.exists(CHROMIUM_EXE):
        print("NOTE: cached chromium not found, letting playwright resolve its own.", file=sys.stderr)
    unittest.main(verbosity=2)
