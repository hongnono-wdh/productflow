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
        self.assertEqual(len(proj["phases"]), 8)
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
            "ready": False, "history": [],
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

    def test_search_refs_autoregisters_orphan_downloads(self):
        # A1 兜底：agent 下载了图但（stub claude 空转）没 done-request → _auto_explore 收尾时
        # 自动把 refs/ 里未登记的图 add-ref，避免超时/漏登记导致 refs=0、成果白丢。
        cp = h.create_project(self.port, "Orphan Refs", slug="orphan-refs")
        pid = cp["id"]
        refs_dir = os.path.join(cp["dir"], ".productflow", "artifacts", "phase-2", "refs")
        os.makedirs(refs_dir, exist_ok=True)
        with open(os.path.join(refs_dir, "1.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")   # 已下载但未登记的参考图
        h.http(self.port, f"/p/{pid}/api/explore", method="POST",
               body={"request": {"kind": "search-refs", "keywords": ["x"]}})
        # 轮询等后台 _auto_explore 收尾（stub claude 空转、很快退出）：refs 已登记 + 请求槽已复位
        got = None
        for _ in range(60):
            _, e = h.http(self.port, f"/p/{pid}/api/explore")
            if e.get("refs") and not e.get("request", {}).get("search-refs"):
                got = e
                break
            time.sleep(0.1)
        self.assertIsNotNone(got, "兜底未在超时内登记 refs / 复位请求槽")
        self.assertIn("artifacts/phase-2/refs/1.png", [r.get("file") for r in got["refs"]])
        self.assertTrue(any(r.get("auto") for r in got["refs"]), "兜底登记项应标 auto=True")

    # ── 系统流程图 GET（生成已移到 ⑤ agent 内联，无 server 生成端点）──
    def test_backend_flow_get_default_when_absent(self):
        cp = h.create_project(self.port, "BF Get", slug="bf-get")
        _, bf = h.http(self.port, f"/p/{cp['id']}/api/backend-flow")
        self.assertEqual(bf, {"version": 1, "nodes": [], "edges": [], "pageLinks": [], "entry": None, "layout": {}})

    def test_product_keys_needs_and_fill_status(self):
        # W6：⑤ 登记第三方 key 需求 → GET 返回需求 + 填写状态；填值后 filled=True 且明文不回吐
        cp = h.create_project(self.port, "PK", slug="pk-demo")
        r = h.cli(["product-key", "add", "--key", "STRIPE_SECRET_KEY", "--desc", "Stripe 支付", "--module", "payment"],
                  self.home, project=cp["dir"])
        self.assertEqual(r.returncode, 0, r.stderr)
        _, body = h.http(self.port, f"/p/{cp['id']}/api/product-keys")
        self.assertEqual(len(body["keys"]), 1)
        k = body["keys"][0]
        self.assertEqual(k["key"], "STRIPE_SECRET_KEY")
        self.assertEqual(k["desc"], "Stripe 支付")
        self.assertFalse(k["filled"])
        # 用户填值（复用 deploy-creds secrets 存储）
        h.http(self.port, f"/p/{cp['id']}/api/deploy-creds", method="POST", body={"creds": {"STRIPE_SECRET_KEY": "sk_test_ABC123"}})
        _, body2 = h.http(self.port, f"/p/{cp['id']}/api/product-keys")
        self.assertTrue(body2["keys"][0]["filled"])
        self.assertNotIn("sk_test_ABC123", json.dumps(body2))   # 明文绝不回吐

    def test_canvas_roundtrip_per_stage(self):
        cp = h.create_project(self.port, "Canvas RT", slug="canvas-rt")
        pid = cp["id"]
        status, body = h.http(self.port, f"/p/{pid}/api/canvas", method="POST",
                              body={"stage": "3", "view": "grid", "items": {"a": 1}, "notes": ["n1"]})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        # GET ?stage=3 returns that stage's cell（只存 view/items/notes；④ 架构图是独立 .mm.md 产物，不入 canvas.json）
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

    def test_imagegen_key_gate(self):
        # 生图硬闸（代码层）：无 key 时 ③④ 出图阶段被服务端拒绝（428 need_imagegen_key），
        # 不静默降级、不 spawn 注定失败的 agent；非出图阶段（⑤）不受影响；配上 key 后放行。
        # 用一台独立、无 key 的 server 验证（共享 server 的沙箱默认带假 key）。
        home = h.make_home()
        os.remove(os.path.join(home, ".config", "openai", "env"))   # 抹掉沙箱默认假 key
        proc, port = h.start_server(home, extra_env={"OPENAI_API_KEY": ""})
        try:
            cp = h.create_project(port, "No Key", slug="no-key")
            pid = cp["id"]
            # ④页面设计（出图阶段）→ 428 硬闸
            status, body = h.http(port, f"/p/{pid}/api/run-stage", method="POST", body={"phase": 4})
            self.assertEqual(status, 428)
            self.assertEqual(body.get("error"), "need_imagegen_key")
            # ⑤功能与数据（非出图）→ 不受闸影响，正常触发（claude stub → 200）
            status, _ = h.http(port, f"/p/{pid}/api/run-stage", method="POST", body={"phase": 5})
            self.assertEqual(status, 200)
            # 配上 key（即用户在握手里提供）后 ④ 放行
            cfg = os.path.join(home, ".config", "openai")
            os.makedirs(cfg, exist_ok=True)
            with open(os.path.join(cfg, "env"), "w") as f:
                f.write('export OPENAI_API_KEY="now-set"\n')
            status, _ = h.http(port, f"/p/{pid}/api/run-stage", method="POST", body={"phase": 4})
            self.assertEqual(status, 200)
        finally:
            h.stop_server(proc)
            h.rm_home(home)

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

    # ---- ③④ 框选局部重绘 (/api/redraw) ----------------------------------

    def _fake_edit_py(self):
        """在沙箱 HOME 放一个假 edit.py 替代真实网络生图：把收到的 --mask 拷一份到
        out-dir/_mask_seen.png（供测试核对蒙版），再写出图 + 打印 'wrote ...'。"""
        d = os.path.join(self.home, ".claude", "skills", "openai-image-gen", "scripts")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "edit.py"), "w") as f:
            f.write(
                "import argparse, os, shutil\n"
                "p=argparse.ArgumentParser()\n"
                "for a in ('--image','--mask','--prompt','--size','--count','--quality',"
                "'--model','--out-dir','--timeout','--api-key'):\n"
                "    p.add_argument(a, action='append' if a=='--image' else 'store')\n"
                "a=p.parse_args()\n"
                "od=getattr(a,'out_dir'); os.makedirs(od, exist_ok=True)\n"
                "if a.mask: shutil.copy(a.mask, os.path.join(od,'_mask_seen.png'))\n"
                "open(os.path.join(od,'edit-01-redraw.png'),'wb').write(b'PNGDUMMY')\n"
                "print('wrote edit-01-redraw.png')\n"
            )

    def test_redraw_inpaint_registers_new_hero_and_mask_is_correct(self):
        from PIL import Image
        self._fake_edit_py()
        cp = h.create_project(self.port, "Redraw Hero", slug="redraw-hero")
        pid, d = cp["id"], cp["dir"]
        src_rel = "artifacts/phase-3/heroes/src.png"
        src = os.path.join(d, ".productflow", src_rel)
        os.makedirs(os.path.dirname(src), exist_ok=True)
        Image.new("RGB", (100, 200), (10, 20, 30)).save(src)
        status, body = h.http(self.port, f"/p/{pid}/api/redraw", method="POST",
            body={"stage": 3, "file": src_rel, "prompt": "把这块配色换浅",
                  "regions": [{"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5}], "platform": "APP"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        # 后台线程把重绘结果作为「新首图」并存进 explore.json（原图不动）
        exp = os.path.join(d, ".productflow", "explore.json")
        def _added():
            try:
                with open(exp) as fh:
                    hs = json.load(fh).get("heroes", [])
            except (OSError, ValueError):
                return False
            return any(x.get("file") == "artifacts/phase-3/edit-01-redraw.png" for x in hs)
        self.assertTrue(self._wait_until(_added), "局部重绘结果应作为新版本并存")
        # 蒙版正确：框选区 alpha=0（重绘），框外 alpha=255（保留），尺寸=原图
        seen = os.path.join(d, ".productflow", "artifacts", "phase-3", "_mask_seen.png")
        self.assertTrue(os.path.isfile(seen))
        m = Image.open(seen).convert("RGBA")
        self.assertEqual(m.size, (100, 200))
        self.assertEqual(m.getpixel((50, 100))[3], 0)    # 区域中心：透明=重绘
        self.assertEqual(m.getpixel((2, 2))[3], 255)     # 角落：不透明=保留

    def _fake_edit_py_chain(self):
        """假 edit.py（链式版）：写**有效 PNG**（让下一块能 PIL 打开）、唯一名、把诉求记进 redraw-calls.log。"""
        d = os.path.join(self.home, ".claude", "skills", "openai-image-gen", "scripts")
        os.makedirs(d, exist_ok=True)
        log = os.path.join(self.home, "redraw-calls.log")
        try:
            os.remove(log)
        except OSError:
            pass
        png_hex = ("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                   "1f15c4890000000d49444154789c6360000002000100ffff0300000006"
                   "0005a3b8c4ad0000000049454e44ae426082")
        with open(os.path.join(d, "edit.py"), "w") as f:
            f.write(
                "import argparse, os\n"
                "p=argparse.ArgumentParser()\n"
                "for a in ('--image','--mask','--prompt','--size','--count','--quality','--model','--out-dir','--timeout','--api-key'):\n"
                "    p.add_argument(a, action='append' if a=='--image' else 'store')\n"
                "a=p.parse_args()\n"
                "od=getattr(a,'out_dir'); os.makedirs(od, exist_ok=True)\n"
                "req=(a.prompt or '').split('本次诉求：')[-1].split(chr(10))[0]\n"
                f"open({log!r},'a').write(req+chr(10))\n"
                f"n=sum(1 for _ in open({log!r}))\n"
                "fn='edit-%02d-redraw.png'%n\n"
                f"open(os.path.join(od,fn),'wb').write(bytes.fromhex({png_hex!r}))\n"
                "print('wrote '+fn)\n"
            )
        return log

    def test_redraw_per_region_sequential(self):
        # 两个框各带不同诉求 → 后端按区域分组、**顺序逐块重绘**（链式），最终登记为「分区重绘」新版本
        from PIL import Image
        log = self._fake_edit_py_chain()
        cp = h.create_project(self.port, "Redraw PerRegion", slug="redraw-pr")
        pid, d = cp["id"], cp["dir"]
        src_rel = "artifacts/phase-3/heroes/src.png"
        src = os.path.join(d, ".productflow", src_rel)
        os.makedirs(os.path.dirname(src), exist_ok=True)
        Image.new("RGB", (120, 200), (10, 20, 30)).save(src)
        status, body = h.http(self.port, f"/p/{pid}/api/redraw", method="POST",
            body={"stage": 3, "file": src_rel, "platform": "APP", "regions": [
                {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.2, "text": "改成蓝色"},
                {"x": 0.6, "y": 0.7, "w": 0.3, "h": 0.2, "text": "放大这块"}]})
        self.assertEqual(status, 200)
        self.assertTrue(self._wait_until(lambda: os.path.isfile(log) and len(open(log).read().splitlines()) >= 2),
                        "应按区域链式调用 edit.py 两次")
        self.assertEqual(open(log).read().splitlines(), ["改成蓝色", "放大这块"], "每块用各自诉求、按序")
        exp = os.path.join(d, ".productflow", "explore.json")

        def _added():
            try:
                hs = json.load(open(exp)).get("heroes", [])
            except (OSError, ValueError):
                return False
            return any("分区重绘" in (x.get("style") or "") for x in hs)
        self.assertTrue(self._wait_until(_added), "分区重绘结果应作为新版本并存")

    def test_redraw_rejects_bad_requests(self):
        from PIL import Image
        cp = h.create_project(self.port, "Redraw Bad", slug="redraw-bad")
        pid, d = cp["id"], cp["dir"]
        src_rel = "artifacts/phase-4/p.png"
        src = os.path.join(d, ".productflow", src_rel)
        os.makedirs(os.path.dirname(src), exist_ok=True)
        Image.new("RGB", (40, 40), (0, 0, 0)).save(src)
        good = {"stage": 4, "file": src_rel, "prompt": "改这块",
                "regions": [{"x": 0, "y": 0, "w": 0.3, "h": 0.3}]}
        for bad in ({**good, "stage": 5},                       # 非法阶段
                    {**good, "file": "artifacts/phase-4/nope.png"},  # 文件不存在
                    {**good, "prompt": "   "},                 # 空描述
                    {**good, "file": "../../etc/passwd"}):     # 穿越
            status, _ = h.http(self.port, f"/p/{pid}/api/redraw", method="POST", body=bad)
            self.assertEqual(status, 400)
        # 空 regions 现在合法：= 整图按这句改（不带蒙版整张重画），应被接受
        status, _ = h.http(self.port, f"/p/{pid}/api/redraw", method="POST", body={**good, "regions": []})
        self.assertEqual(status, 200)

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


class BriefHistoryTest(unittest.TestCase):
    """重新生成摘要：每轮都覆盖 summary、清 request（前端按钮恢复）、追加一版 history。
    用「真出 JSON 的 claude 桩」（计数器 → 每轮 goal 不同）驱动多轮，验证不丢历史、每轮都更新。"""

    def setUp(self):
        self.home = h.make_home()
        stub = os.path.join(self.home, "bin", "claude")
        with open(stub, "w") as f:
            f.write(
                "#!/usr/bin/env python3\n"
                "import os, json\n"
                "c = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.n')\n"
                "try: n = int(open(c).read()) + 1\n"
                "except Exception: n = 1\n"
                "open(c, 'w').write(str(n))\n"
                "s = {'goal': 'G%d' % n, 'users': 'U', 'need': 'N', 'scope': 'S', 'questions': []}\n"
                "print(json.dumps({'type': 'result', 'result': json.dumps(s)}))\n"
            )
        os.chmod(stub, 0o755)
        self.proc, self.port = h.start_server(self.home)

    def tearDown(self):
        h.stop_server(self.proc)
        h.rm_home(self.home)

    def test_regenerate_updates_summary_and_appends_history(self):
        cp = h.create_project(self.port, "Brief History", slug="brief-hist")
        pid, pdir = cp["id"], cp["dir"]
        bp = os.path.join(pdir, ".productflow", "brief.json")
        br = {}
        for rnd in (1, 2, 3):
            h.http(self.port, f"/p/{pid}/api/brief", method="POST",
                   body={"description": f"d{rnd}", "confirmed": False,
                         "request": {"kind": "gen-summary", "description": f"d{rnd}"}})
            for _ in range(80):
                try:
                    with open(bp) as f:
                        br = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    br = {}
                if len(br.get("history", [])) >= rnd and br.get("ready") and br.get("request") is None:
                    break
                time.sleep(0.2)
            self.assertEqual(len(br.get("history", [])), rnd, f"round {rnd}: history should grow")
            self.assertEqual(br["summary"]["goal"], "G%d" % rnd, f"round {rnd}: summary must update")
            self.assertIsNone(br["request"], f"round {rnd}: request cleared → 前端按钮恢复")
            self.assertTrue(br["ready"], f"round {rnd}: ready")
        self.assertEqual([v["summary"]["goal"] for v in br["history"]], ["G1", "G2", "G3"])


if __name__ == "__main__":
    unittest.main()
