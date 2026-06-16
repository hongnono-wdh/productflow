"""HTTP API tests for server.py.

One isolated server is started in setUpClass (sandboxed HOME via make_home),
torn down in tearDownClass. Every test uses a distinct project name/slug so the
shared registry never causes cross-test interference.

helpers.http() sends header-less urllib requests (Host=127.0.0.1, no Origin /
Sec-Fetch), so it passes the anti-rebinding guard. To exercise the security
checks we build our own urllib requests with the offending headers (_raw()).
"""
import json
import os
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import helpers as h  # noqa: E402


def _raw(port, path, method="GET", headers=None, body=None):
    """Send a request with arbitrary headers (to exercise the security guard).

    Returns (status_code, raw_text_body).
    """
    url = f"http://127.0.0.1:{port}{path}"
    data = None
    hh = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        hh.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hh, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as ex:
        raw = ex.read().decode()
        ex.close()
        return ex.code, raw


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = h.make_home()
        cls.proc, cls.port = h.start_server(cls.home)

    @classmethod
    def tearDownClass(cls):
        h.stop_server(cls.proc)
        h.rm_home(cls.home)

    # ---- meta / listing -------------------------------------------------

    def test_version(self):
        status, body = h.http(self.port, "/api/version")
        self.assertEqual(status, 200)
        # 版本以 skill 根目录 VERSION 文件为准（自动更新机制的单一来源）
        with open(os.path.join(os.path.dirname(__file__), "..", "VERSION")) as f:
            ver = f.read().strip()
        self.assertEqual(body, {"app": "productflow", "version": ver})

    def test_update_check_shape(self):
        # 自动更新：当前版本 vs 远端版本。测试环境不联网，latest 应为 None、不报有更新。
        status, body = h.http(self.port, "/api/update-check")
        self.assertEqual(status, 200)
        with open(os.path.join(os.path.dirname(__file__), "..", "VERSION")) as f:
            ver = f.read().strip()
        self.assertEqual(body["current"], ver)
        self.assertIn("latest", body)
        self.assertFalse(body["update_available"])   # 无远端版本时绝不提示更新
        self.assertIn("repo", body)
        self.assertIn("git", body)

    def test_update_rejects_non_git_checkout(self):
        # 非 git 安装时 /api/update 必须拒绝（400 not_git_checkout），绝不瞎跑 git pull。
        # 若开发机的 skill 目录恰好已是 git 仓库（发布后），跳过——不能在测试里跑真实 git pull。
        skill_dir = os.path.dirname(os.path.dirname(__file__))
        is_git = subprocess.run(["git", "-C", skill_dir, "rev-parse", "--show-toplevel"],
                                capture_output=True).returncode == 0
        if is_git:
            self.skipTest("skill dir 是 git 仓库；/api/update 会跑真实 git pull，跳过")
        status, body = h.http(self.port, "/api/update", method="POST", body={})
        self.assertEqual(status, 400)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "not_git_checkout")

    def test_projects_shape_and_create_reflected(self):
        # The shared registry may already hold projects from other tests, so we
        # assert structure + that a freshly created project shows up by id.
        status, body = h.http(self.port, "/api/projects")
        self.assertEqual(status, 200)
        self.assertIn("version", body)
        self.assertIsInstance(body["projects"], list)
        self.assertIsInstance(body["pending"], list)

        cp = h.create_project(self.port, "Listing Probe", slug="listing-probe")
        status, body = h.http(self.port, "/api/projects")
        match = [p for p in body["projects"] if p["id"] == cp["id"]]
        self.assertEqual(len(match), 1)
        proj = match[0]
        self.assertEqual(proj["name"], "Listing Probe")
        self.assertEqual(proj["done"], 0)
        self.assertEqual(proj["current_phase"], 1)
        self.assertEqual(len(proj["phases"]), 7)
        self.assertFalse(proj["missing"])
        self.assertFalse(proj["error"])
        self.assertFalse(proj["archived"])

    # ---- security guard (needs custom headers) --------------------------

    def test_host_header_not_allowed_403(self):
        status, _ = _raw(self.port, "/api/version", headers={"Host": "evil.example.com"})
        self.assertEqual(status, 403)

    def test_host_header_localhost_ok(self):
        status, _ = _raw(self.port, "/api/version", headers={"Host": "localhost"})
        self.assertEqual(status, 200)

    def test_host_header_127_ok(self):
        status, _ = _raw(self.port, "/api/version", headers={"Host": "127.0.0.1"})
        self.assertEqual(status, 200)

    def test_post_origin_mismatch_403(self):
        status, _ = _raw(self.port, "/api/pending", method="POST",
                         headers={"Origin": "http://evil.example.com"},
                         body={"name": "origin-bad"})
        self.assertEqual(status, 403)

    def test_post_origin_match_ok(self):
        status, _ = _raw(self.port, "/api/pending", method="POST",
                         headers={"Origin": "http://127.0.0.1"},
                         body={"name": "origin-ok"})
        self.assertEqual(status, 200)

    def test_post_sec_fetch_cross_site_403(self):
        status, _ = _raw(self.port, "/api/pending", method="POST",
                         headers={"Sec-Fetch-Site": "cross-site"},
                         body={"name": "sfs-cross"})
        self.assertEqual(status, 403)

    def test_post_sec_fetch_same_origin_ok(self):
        status, _ = _raw(self.port, "/api/pending", method="POST",
                         headers={"Sec-Fetch-Site": "same-origin"},
                         body={"name": "sfs-same"})
        self.assertEqual(status, 200)

    def test_get_ignores_origin_header(self):
        # GET only validates Host; an Origin header alone does not block it.
        status, _ = _raw(self.port, "/api/version", method="GET",
                         headers={"Origin": "http://evil.example.com"})
        self.assertEqual(status, 200)

    def test_no_security_headers_ok(self):
        status, body = h.http(self.port, "/api/version")
        self.assertEqual(status, 200)
        self.assertEqual(body["app"], "productflow")

    # ---- /api/create ----------------------------------------------------

    def test_create_with_explicit_slug(self):
        cp = h.create_project(self.port, "Slug Explicit", slug="slug-explicit")
        self.assertTrue(cp["ok"])
        self.assertEqual(os.path.basename(cp["dir"]), "slug-explicit")
        # id is "{slug}-{randomhex}" — directory uses slug, registry id adds suffix
        self.assertTrue(cp["id"].startswith("slug-explicit-"))
        self.assertTrue(os.path.isdir(os.path.join(cp["dir"], ".productflow")))

    def test_create_pure_chinese_name_slug_fallback(self):
        # Pure-Chinese name -> _slug() == "project" -> server gives "project-XXXX".
        cp = h.create_project(self.port, "纯中文项目名")
        base = os.path.basename(cp["dir"])
        self.assertTrue(base.startswith("project-"), base)
        self.assertEqual(cp["id"][: len("project-")], "project-")

    def test_create_duplicate_slug_gets_suffix(self):
        first = h.create_project(self.port, "Dup One", slug="dup-slug")
        second = h.create_project(self.port, "Dup Two", slug="dup-slug")
        self.assertEqual(os.path.basename(first["dir"]), "dup-slug")
        self.assertEqual(os.path.basename(second["dir"]), "dup-slug-2")

    def test_create_name_only_slug_from_name(self):
        cp = h.create_project(self.port, "Name Only App")
        self.assertEqual(os.path.basename(cp["dir"]), "name-only-app")

    # ---- /api/pending ---------------------------------------------------

    def test_pending_write_and_reflected_in_projects(self):
        status, body = h.http(self.port, "/api/pending", method="POST",
                              body={"name": "PendingReflect", "brief": "ship it"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["file"].endswith(".json"))

        status, payload = h.http(self.port, "/api/projects")
        names = [p["name"] for p in payload["pending"]]
        self.assertIn("PendingReflect", names)
        entry = next(p for p in payload["pending"] if p["name"] == "PendingReflect")
        self.assertEqual(entry["brief"], "ship it")
        self.assertIsNotNone(entry["created"])

    def test_pending_empty_name_rejected(self):
        status, body = h.http(self.port, "/api/pending", method="POST",
                              body={"name": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "empty_name")

    # ---- per-project GET defaults (file missing) ------------------------

    def test_project_get_defaults(self):
        cp = h.create_project(self.port, "Defaults Probe", slug="defaults-probe")
        pid = cp["id"]

        # state exists after create
        status, _ = h.http(self.port, f"/p/{pid}/api/state")
        self.assertEqual(status, 200)

        status, inbox = h.http(self.port, f"/p/{pid}/api/inbox")
        self.assertEqual(status, 200)
        self.assertEqual(inbox, {"messages": []})

        status, canvas = h.http(self.port, f"/p/{pid}/api/canvas")
        self.assertEqual(status, 200)
        self.assertEqual(canvas, {"view": None, "items": {}, "notes": []})

        status, health = h.http(self.port, f"/p/{pid}/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health, {})

        status, pages = h.http(self.port, f"/p/{pid}/api/pages")
        self.assertEqual(status, 200)
        self.assertEqual(pages, {"pages": []})

        status, explore = h.http(self.port, f"/p/{pid}/api/explore")
        self.assertEqual(status, 200)
        self.assertEqual(explore, {
            "stylePrefs": [], "request": {}, "refs": [], "selectedRefs": [],
            "styleSummary": "", "heroes": [], "selectedHero": "",
        })

        status, brief = h.http(self.port, f"/p/{pid}/api/brief")
        self.assertEqual(status, 200)
        self.assertEqual(brief, {
            "description": "", "request": None, "questions": [], "confirmed": False,
            "summary": {"goal": "", "users": "", "need": "", "scope": ""},
            "ready": False,
        })

    def test_brief_confirm_persists_without_spawn(self):
        # 「确认需求」：POST description + questions=[] + confirmed=true，无 request → 不跑 AI，落盘可读回
        cp = h.create_project(self.port, "Brief Confirm", slug="brief-confirm")
        pid = cp["id"]
        status, _ = h.http(self.port, f"/p/{pid}/api/brief", method="POST",
                           body={"description": "确认后的需求", "questions": [], "confirmed": True})
        self.assertEqual(status, 200)
        _, b = h.http(self.port, f"/p/{pid}/api/brief")
        self.assertEqual(b["description"], "确认后的需求")
        self.assertEqual(b["questions"], [])
        self.assertTrue(b["confirmed"])

    # ---- POST round-trips ------------------------------------------------

    def test_brief_roundtrip_and_inbox_entry(self):
        cp = h.create_project(self.port, "Brief RT", slug="brief-rt")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/brief", method="POST",
                              body={"description": "my product", "request": {"kind": "summary"}})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

        status, brief = h.http(self.port, f"/p/{pid}/api/brief")
        self.assertEqual(brief["description"], "my product")
        self.assertEqual(brief["request"], {"kind": "summary"})
        self.assertFalse(brief["ready"])

        status, inbox = h.http(self.port, f"/p/{pid}/api/inbox")
        types = [m.get("type") for m in inbox["messages"]]
        self.assertIn("brief-request", types)
        entry = next(m for m in inbox["messages"] if m.get("type") == "brief-request")
        self.assertEqual(entry["from"], "web")
        self.assertEqual(entry["request"], {"kind": "summary"})

    def test_explore_roundtrip_and_inbox_entry(self):
        cp = h.create_project(self.port, "Explore RT", slug="explore-rt")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/explore", method="POST",
                              body={"stylePrefs": ["minimal", "bold"],
                                    "request": {"kind": "search-refs", "keywords": ["fintech"]}})
        self.assertEqual(status, 200)

        status, explore = h.http(self.port, f"/p/{pid}/api/explore")
        self.assertEqual(explore["stylePrefs"], ["minimal", "bold"])
        # 按 kind 分槽存储
        self.assertEqual(explore["request"], {"search-refs": {"kind": "search-refs", "keywords": ["fintech"]}})

        status, inbox = h.http(self.port, f"/p/{pid}/api/inbox")
        types = [m.get("type") for m in inbox["messages"]]
        self.assertIn("explore-request", types)
        entry = next(m for m in inbox["messages"] if m.get("type") == "explore-request")
        self.assertEqual(entry["request"], {"kind": "search-refs", "keywords": ["fintech"]})

    def test_canvas_roundtrip_per_stage(self):
        cp = h.create_project(self.port, "Canvas RT", slug="canvas-rt")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/canvas", method="POST",
                              body={"stage": "3", "view": "grid", "items": {"a": 1}, "notes": ["n1"]})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        # GET ?stage=3 returns that stage's cell
        status, canvas = h.http(self.port, f"/p/{pid}/api/canvas?stage=3")
        self.assertEqual(canvas, {"view": "grid", "items": {"a": 1}, "notes": ["n1"]})

    def test_canvas_per_stage_isolation(self):
        # 守 P0 覆盖写 bug：P3 与 P4 两块画布各自持久化、互不覆盖
        cp = h.create_project(self.port, "Canvas Iso", slug="canvas-iso")
        pid = cp["id"]
        h.http(self.port, f"/p/{pid}/api/canvas", method="POST",
               body={"stage": "3", "view": "hero", "items": {"h": 1}, "notes": []})
        h.http(self.port, f"/p/{pid}/api/canvas", method="POST",
               body={"stage": "4", "view": "pages", "items": {"p": 2}, "notes": ["x"]})
        _, c3 = h.http(self.port, f"/p/{pid}/api/canvas?stage=3")
        _, c4 = h.http(self.port, f"/p/{pid}/api/canvas?stage=4")
        self.assertEqual(c3["items"], {"h": 1})     # 写 stage4 没抹掉 stage3
        self.assertEqual(c4["items"], {"p": 2})
        self.assertEqual(c3["view"], "hero")
        self.assertEqual(c4["view"], "pages")

    def test_canvas_bad_stage_rejected(self):
        cp = h.create_project(self.port, "Canvas Bad", slug="canvas-bad")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/canvas", method="POST",
                              body={"stage": "9", "view": "x"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "bad_stage")

    def test_pages_add_and_remove(self):
        cp = h.create_project(self.port, "Pages RT", slug="pages-rt")
        pid = cp["id"]

        status, body = h.http(self.port, f"/p/{pid}/api/pages", method="POST",
                              body={"action": "add", "name": "Home", "group": "Main"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

        status, pages = h.http(self.port, f"/p/{pid}/api/pages")
        self.assertEqual(len(pages["pages"]), 1)
        page = pages["pages"][0]
        self.assertEqual(page["name"], "Home")
        self.assertEqual(page["group"], "Main")
        self.assertEqual(page["status"], "placeholder")
        self.assertTrue(page["id"].startswith("pg-"))

        status, body = h.http(self.port, f"/p/{pid}/api/pages", method="POST",
                              body={"action": "remove", "id": page["id"]})
        self.assertEqual(status, 200)
        status, pages = h.http(self.port, f"/p/{pid}/api/pages")
        self.assertEqual(pages["pages"], [])

    def test_pages_add_empty_name_rejected(self):
        cp = h.create_project(self.port, "Pages Empty", slug="pages-empty")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/pages", method="POST",
                              body={"action": "add", "name": "  "})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "empty_name")

    def test_pages_bad_action_rejected(self):
        cp = h.create_project(self.port, "Pages Bad", slug="pages-bad")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/pages", method="POST",
                              body={"action": "frobnicate"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "bad_action")

    def test_inbox_plain_text_post(self):
        cp = h.create_project(self.port, "Inbox Text", slug="inbox-text")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/inbox", method="POST",
                              body={"text": "hello there", "extra": "kept"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

        status, inbox = h.http(self.port, f"/p/{pid}/api/inbox")
        entry = inbox["messages"][-1]
        self.assertEqual(entry["text"], "hello there")
        self.assertEqual(entry["from"], "web")
        self.assertEqual(entry["extra"], "kept")  # extra keys merged in

    def test_inbox_empty_text_rejected(self):
        cp = h.create_project(self.port, "Inbox Empty", slug="inbox-empty")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/inbox", method="POST",
                              body={"text": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "empty")

    # ---- bad ids / path traversal / disallowed subs ---------------------

    def test_get_path_traversal_id_404(self):
        # Encoded "../../etc" never matches the [a-z0-9-] id pattern.
        status, _ = _raw(self.port, "/p/..%2F..%2Fetc/api/state")
        self.assertEqual(status, 404)

    def test_get_uppercase_id_404(self):
        # Non-whitelisted chars (uppercase) fall outside P_ROUTE -> 404.
        status, _ = _raw(self.port, "/p/ABC/api/state")
        self.assertEqual(status, 404)

    def test_get_unknown_id_404(self):
        status, _ = h.http(self.port, "/p/nonexistent-zzzz/api/state")
        self.assertEqual(status, 404)

    def test_post_disallowed_sub_404(self):
        cp = h.create_project(self.port, "Sub Probe", slug="sub-probe")
        pid = cp["id"]
        # /api/state is read-only; POST to it is not in the allow list.
        status, _ = h.http(self.port, f"/p/{pid}/api/state", method="POST", body={"x": 1})
        self.assertEqual(status, 404)

    def test_post_unknown_id_404(self):
        status, _ = h.http(self.port, "/p/nonexistent-zzzz/api/inbox",
                           method="POST", body={"text": "x"})
        self.assertEqual(status, 404)

    def test_post_bad_json_400(self):
        # Empty body with good headers -> json.loads fails -> bad_json.
        status, raw = _raw(self.port, "/api/create", method="POST",
                           headers={"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(raw), {"error": "bad_json"})

    def test_unknown_route_404(self):
        status, _ = h.http(self.port, "/api/does-not-exist")
        self.assertEqual(status, 404)

    # ---- /api/wizard (创建时写的平台，面板读) -----------------------------

    def test_wizard_get_default(self):
        cp = h.create_project(self.port, "Wizard Default", slug="wizard-default")
        pid = cp["id"]
        status, wz = h.http(self.port, f"/p/{pid}/api/wizard")
        self.assertEqual(status, 200)
        self.assertEqual(wz, {"brief": "", "platforms": [], "primary": None,
                              "priority": [], "stylePrefs": []})

    def test_project_config_endpoint_removed(self):
        # /api/project-config 已废弃（新模型阶段内不改平台配置）→ 不在白名单 → 404
        cp = h.create_project(self.port, "Cfg Gone", slug="cfg-gone")
        pid = cp["id"]
        status, _ = h.http(self.port, f"/p/{pid}/api/project-config", method="POST",
                           body={"platforms": ["PC"]})
        self.assertEqual(status, 404)

    # ---- delete project: remove (keep files) vs delete (remove dir) ------

    def _reg_path(self, pid):
        return os.path.join(self.home, ".productflow", "projects", pid + ".json")

    def test_project_remove_keeps_files(self):
        cp = h.create_project(self.port, "Rm Keep", slug="rm-keep")
        pid, d = cp["id"], cp["dir"]
        self.assertTrue(os.path.isdir(d))
        self.assertTrue(os.path.exists(self._reg_path(pid)))
        status, body = h.http(self.port, "/api/project-remove", method="POST", body={"id": pid})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertFalse(os.path.exists(self._reg_path(pid)))  # 注册表条目删
        self.assertTrue(os.path.isdir(d))                       # 磁盘文件保留

    def test_project_delete_removes_files(self):
        cp = h.create_project(self.port, "Del Hard", slug="del-hard")
        pid, d = cp["id"], cp["dir"]
        status, body = h.http(self.port, "/api/project-delete", method="POST", body={"id": pid})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertFalse(os.path.exists(self._reg_path(pid)))  # 注册表删
        self.assertFalse(os.path.isdir(d))                      # 磁盘文件夹删

    def test_project_delete_bad_id_400(self):
        status, body = h.http(self.port, "/api/project-delete", method="POST", body={"id": "../../etc"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "bad_id")

    def test_vendor_serves_viewer_assets(self):
        # 图片查看器 Viewer.js 必须能从 /vendor/ 取到（否则前端 ②找参考 放大功能挂掉）
        for name, ctype_part in (("viewer.min.js", "javascript"), ("viewer.min.css", "css")):
            url = f"http://127.0.0.1:{self.port}/vendor/{name}"
            with urllib.request.urlopen(url, timeout=8) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn(ctype_part, resp.headers.get("Content-Type", ""))
                self.assertGreater(len(resp.read()), 1000)
        # 白名单外的 vendor 文件仍 404
        status, _ = _raw(self.port, "/vendor/evil.js")
        self.assertEqual(status, 404)

    def test_choice_get_default_and_answer(self):
        cp = h.create_project(self.port, "Choice T", slug="choice-t")
        pid = cp["id"]
        # 默认空
        status, ch = h.http(self.port, f"/p/{pid}/api/choices")
        self.assertEqual(ch, {"choices": []})
        # CLI 抛一个问题（agent 侧）
        r = h.cli(["choice", "ask", "--question", "A 还是 B？", "--option", "A", "--option", "B"],
                  self.home, project=cp["dir"])
        cid = r.stdout.strip()
        # 前端答复
        status, body = h.http(self.port, f"/p/{pid}/api/choice", method="POST",
                              body={"id": cid, "answer": "B"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, ch = h.http(self.port, f"/p/{pid}/api/choices")
        self.assertEqual(ch["choices"][0]["answer"], "B")

    def test_run_stage_trigger_and_validation(self):
        cp = h.create_project(self.port, "Run Stage", slug="run-stage")
        pid = cp["id"]
        # 合法阶段：触发，落 inbox stage-request（claude stub 不真跑）
        status, body = h.http(self.port, f"/p/{pid}/api/run-stage", method="POST",
                              body={"phase": 5, "instruction": "用 SQLite"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, ib = h.http(self.port, f"/p/{pid}/api/inbox")
        self.assertTrue(any(m.get("type") == "stage-request" for m in ib["messages"]))
        # 非法阶段 → 400
        status, _ = h.http(self.port, f"/p/{pid}/api/run-stage", method="POST", body={"phase": 99})
        self.assertEqual(status, 400)
        status, _ = h.http(self.port, f"/p/{pid}/api/run-stage", method="POST", body={"phase": "x"})
        self.assertEqual(status, 400)

    def test_deploy_creds_roundtrip_masked_merge_and_perms(self):
        cp = h.create_project(self.port, "Deploy Creds", slug="deploy-creds")
        pid = cp["id"]
        # 默认空
        _, g = h.http(self.port, f"/p/{pid}/api/deploy-creds")
        self.assertEqual(g, {"keys": []})
        # 存两项
        _, b = h.http(self.port, f"/p/{pid}/api/deploy-creds", method="POST",
                      body={"creds": {"PF_SSH_HOST": "1.2.3.4", "PF_SSH_USER": "root"}})
        self.assertTrue(b["ok"])
        self.assertEqual(b["count"], 2)
        # GET 只回脱敏键，绝不回吐明文
        _, g = h.http(self.port, f"/p/{pid}/api/deploy-creds")
        keys = {k["key"]: k["masked"] for k in g["keys"]}
        self.assertEqual(set(keys), {"PF_SSH_HOST", "PF_SSH_USER"})
        self.assertNotIn("1.2.3.4", json.dumps(g))
        self.assertTrue(keys["PF_SSH_HOST"].endswith("3.4"))
        # 合并：只补一项，已存的不丢
        _, b = h.http(self.port, f"/p/{pid}/api/deploy-creds", method="POST",
                      body={"creds": {"PF_SSH_PORT": "22"}})
        self.assertEqual(b["count"], 3)
        # 落盘在项目仓库外的 secrets/<id>.env，且 600 权限
        secrets = os.path.join(self.home, ".productflow", "secrets", pid + ".env")
        self.assertTrue(os.path.exists(secrets))
        self.assertEqual(oct(os.stat(secrets).st_mode & 0o777), "0o600")
        self.assertFalse(secrets.startswith(os.path.join(cp["dir"], "")))
        # 非法 body → 400
        status, _ = h.http(self.port, f"/p/{pid}/api/deploy-creds", method="POST", body={"creds": "nope"})
        self.assertEqual(status, 400)

    def test_deploy_creds_remove_clear_and_special_chars(self):
        cp = h.create_project(self.port, "Creds RM", slug="creds-rm")
        pid = cp["id"]
        # 含特殊字符的 token 不被静默改坏（往返一致，经 mask 间接验证：删时按原 key）
        h.http(self.port, f"/p/{pid}/api/deploy-creds", method="POST",
               body={"creds": {"PF_SSH_HOST": "1.1.1.1", "CF_API_TOKEN": 'a"b$c`d'}})
        secrets = os.path.join(self.home, ".productflow", "secrets", pid + ".env")
        # 删单条
        h.http(self.port, f"/p/{pid}/api/deploy-creds", method="POST", body={"remove": "PF_SSH_HOST"})
        _, g = h.http(self.port, f"/p/{pid}/api/deploy-creds")
        self.assertEqual([k["key"] for k in g["keys"]], ["CF_API_TOKEN"])
        # 含特殊字符的值仍在文件里、且文件未泄明文给网页（只回脱敏）
        self.assertNotIn('a"b$c`d', json.dumps(g))
        # 清空全部
        h.http(self.port, f"/p/{pid}/api/deploy-creds", method="POST", body={"clear": True})
        _, g = h.http(self.port, f"/p/{pid}/api/deploy-creds")
        self.assertEqual(g["keys"], [])

    def test_page_gen_version_trigger_and_validation(self):
        cp = h.create_project(self.port, "Page Ver", slug="page-ver")
        pid = cp["id"]
        # 先加一个页面
        h.http(self.port, f"/p/{pid}/api/pages", method="POST",
               body={"action": "add", "name": "注册页", "group": "登录"})
        status, pages = h.http(self.port, f"/p/{pid}/api/pages")
        page_id = pages["pages"][0]["id"]
        # 合法：生成某平台版本 → 200 + inbox page-version-request
        status, body = h.http(self.port, f"/p/{pid}/api/pages", method="POST",
                              body={"action": "gen-version", "id": page_id, "platform": "H5"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, ib = h.http(self.port, f"/p/{pid}/api/inbox")
        self.assertTrue(any(m.get("type") == "page-version-request" for m in ib["messages"]))
        # 非法平台 → 400
        status, _ = h.http(self.port, f"/p/{pid}/api/pages", method="POST",
                           body={"action": "gen-version", "id": page_id, "platform": "X"})
        self.assertEqual(status, 400)
        # 不存在的页面 → 400
        status, _ = h.http(self.port, f"/p/{pid}/api/pages", method="POST",
                           body={"action": "gen-version", "id": "pg-zzz", "platform": "PC"})
        self.assertEqual(status, 400)

    def _wait_until(self, fn, tries=40, gap=0.1):
        for _ in range(tries):
            if fn():
                return True
            time.sleep(gap)
        return False

    def test_explore_stuck_request_auto_cleared(self):
        # claude stub 是 no-op、永不 done-request → 卡住的 request 槽必须被后台自动清掉（否则前端一直转）
        cp = h.create_project(self.port, "Stuck Ref", slug="stuck-ref")
        pid = cp["id"]
        h.http(self.port, f"/p/{pid}/api/explore", method="POST",
               body={"request": {"kind": "search-refs", "keywords": "x", "product": "y"}})

        def cleared():
            _, ex = h.http(self.port, f"/p/{pid}/api/explore")
            return "search-refs" not in (ex.get("request") or {})
        self.assertTrue(self._wait_until(cleared), "卡住的 search-refs 请求槽未被自动清除")

    def test_brief_stuck_request_cleared_on_failure(self):
        # 生成摘要失败（stub 无输出→解析失败）也要清掉 request 槽，前端停转、可重试
        cp = h.create_project(self.port, "Stuck Brief", slug="stuck-brief")
        pid = cp["id"]
        h.http(self.port, f"/p/{pid}/api/brief", method="POST",
               body={"description": "一个测试产品",
                     "request": {"kind": "gen-summary", "description": "一个测试产品"}})

        def cleared():
            _, b = h.http(self.port, f"/p/{pid}/api/brief")
            return not b.get("request")
        self.assertTrue(self._wait_until(cleared), "失败后 brief 的 request 槽未被清除")

    def test_research_trigger_posts_inbox(self):
        # 「让 Agent 做市场调研」：投 inbox research-request（claude 由 stub 兜底，不真跑）
        cp = h.create_project(self.port, "Research T", slug="research-t")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/research", method="POST", body={})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, inbox = h.http(self.port, f"/p/{pid}/api/inbox")
        self.assertIn("research-request", [m.get("type") for m in inbox["messages"]])


if __name__ == "__main__":
    unittest.main()
