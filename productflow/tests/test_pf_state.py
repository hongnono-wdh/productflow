"""Unit tests for pf_state.py CLI state machine (subprocess via cli(), no server).

Isolation: every test gets a throwaway HOME (make_home) so PF_HOME (~/.productflow)
and the project dir live in a temp sandbox; tearDown removes it. The project dir is
created under <home>/code/<slug> and we drive pf_state via the `project=` arg of cli()
(which sets PF_PROJECT), or explicit --dir for env-vs-flag cases.

Note: `status` prints human-readable text (NOT JSON), so state assertions read
<dir>/.productflow/state.json directly. `explore show` / `brief show` are JSON.
"""
import json
import os
import re
import sys
import unittest

# Make the shared harness importable whether this module is loaded as
# `tests.test_pf_state` (tests/ not a package) or via `unittest discover`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers import cli, make_home, rm_home


def read_state(d):
    with open(os.path.join(d, ".productflow", "state.json"), encoding="utf-8") as f:
        return json.load(f)


def read_json_file(d, name):
    with open(os.path.join(d, ".productflow", name), encoding="utf-8") as f:
        return json.load(f)


class PfStateBase(unittest.TestCase):
    PRODUCT = "Test Product"

    def setUp(self):
        self.home = make_home()
        self.dir = os.path.join(self.home, "code", "testproj")
        os.makedirs(self.dir, exist_ok=True)
        r = cli(["init", "--product", self.PRODUCT], self.home, project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        # init stdout: "initialized <root> (id: <pid>)"
        m = re.search(r"\(id: ([a-z0-9-]+)\)", r.stdout)
        self.assertIsNotNone(m, f"could not parse id from: {r.stdout!r}")
        self.pid = m.group(1)

    def tearDown(self):
        rm_home(self.home)

    def run_ok(self, args):
        r = cli(args, self.home, project=self.dir)
        self.assertEqual(r.returncode, 0, f"{args} -> rc={r.returncode}: {r.stderr}")
        return r


class TestInit(PfStateBase):
    def test_state_json_created_with_fields(self):
        self.assertTrue(os.path.isfile(os.path.join(self.dir, ".productflow", "state.json")))
        s = read_state(self.dir)
        self.assertEqual(s["product"], self.PRODUCT)
        self.assertEqual(s["id"], self.pid)
        self.assertEqual(s["v"], 2)
        self.assertEqual(s["current_phase"], 1)
        self.assertEqual(s["project_dir"], os.path.abspath(self.dir))
        self.assertEqual(len(s["phases"]), 8)
        self.assertEqual([ph["name"] for ph in s["phases"]],
                         ["市场调研", "找参考", "首图设计", "页面设计",
                          "功能与数据设计", "前端实现", "后端实现 · 测试", "部署上线"])
        # phases / steps all start pending
        self.assertTrue(all(ph["status"] == "pending" for ph in s["phases"]))
        self.assertTrue(all(st["status"] == "pending"
                            for ph in s["phases"] for st in ph["steps"]))
        # init writes one log line
        self.assertEqual(len(s["log"]), 1)
        self.assertIn(self.PRODUCT, s["log"][0]["msg"])

    def test_id_format_slug_plus_4hex(self):
        # _slug("Test Product") -> "test-product"; suffix = urandom(2).hex() = 4 hex chars
        self.assertRegex(self.pid, r"^test-product-[0-9a-f]{4}$")

    def test_id_registered_in_home_registry(self):
        reg = os.path.join(self.home, ".productflow", "projects", self.pid + ".json")
        self.assertTrue(os.path.isfile(reg))
        entry = read_json_file(self.home, os.path.join("projects", self.pid + ".json"))
        self.assertEqual(entry["id"], self.pid)
        self.assertEqual(entry["path"], os.path.abspath(self.dir))
        self.assertEqual(entry["archived"], False)

    def test_phase_artifact_dirs_created(self):
        for pid in range(1, 6):
            self.assertTrue(os.path.isdir(
                os.path.join(self.dir, ".productflow", "artifacts", f"phase-{pid}")))

    def test_inbox_jsonl_created_empty(self):
        p = os.path.join(self.dir, ".productflow", "inbox.jsonl")
        self.assertTrue(os.path.isfile(p))
        with open(p, encoding="utf-8") as f:
            self.assertEqual(f.read(), "")

    def test_reinit_without_force_fails(self):
        r = cli(["init", "--product", "Other"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("state already exists", r.stderr)
        # original product untouched
        self.assertEqual(read_state(self.dir)["product"], self.PRODUCT)

    def test_reinit_with_force_resets(self):
        old_id = self.pid
        r = cli(["init", "--product", "Reset Product", "--force"], self.home, project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        s = read_state(self.dir)
        self.assertEqual(s["product"], "Reset Product")
        # force creates a fresh id (new random suffix)
        self.assertNotEqual(s["id"], old_id)
        self.assertRegex(s["id"], r"^reset-product-[0-9a-f]{4}$")


class TestPhaseStep(PfStateBase):
    def test_phase_active_sets_current_phase(self):
        r = self.run_ok(["phase", "2", "--status", "active"])
        self.assertEqual(r.stdout.strip(), "phase 2 = active")
        s = read_state(self.dir)
        ph2 = next(p for p in s["phases"] if p["id"] == 2)
        self.assertEqual(ph2["status"], "active")
        self.assertEqual(s["current_phase"], 2)

    def test_phase_done_keeps_current_phase(self):
        self.run_ok(["phase", "2", "--status", "active"])  # current -> 2
        self.run_ok(["phase", "2", "--status", "done"])
        s = read_state(self.dir)
        ph2 = next(p for p in s["phases"] if p["id"] == 2)
        self.assertEqual(ph2["status"], "done")
        # done does NOT touch current_phase
        self.assertEqual(s["current_phase"], 2)

    def test_phase_logs_appended(self):
        before = len(read_state(self.dir)["log"])
        self.run_ok(["phase", "3", "--status", "active"])
        s = read_state(self.dir)
        self.assertEqual(len(s["log"]), before + 1)
        self.assertIn("P3", s["log"][-1]["msg"])

    def test_step_status_done(self):
        r = self.run_ok(["step", "1", "define-product", "--status", "done"])
        self.assertEqual(r.stdout.strip(), "P1/define-product = done")
        s = read_state(self.dir)
        ph1 = next(p for p in s["phases"] if p["id"] == 1)
        st = next(x for x in ph1["steps"] if x["id"] == "define-product")
        self.assertEqual(st["status"], "done")

    def test_step_status_active_and_skipped(self):
        self.run_ok(["step", "1", "search-competitors", "--status", "active"])
        self.run_ok(["step", "1", "analyze-style", "--status", "skipped"])
        s = read_state(self.dir)
        ph1 = next(p for p in s["phases"] if p["id"] == 1)
        statuses = {x["id"]: x["status"] for x in ph1["steps"]}
        self.assertEqual(statuses["search-competitors"], "active")
        self.assertEqual(statuses["analyze-style"], "skipped")

    def test_step_unknown_id_fails(self):
        r = cli(["step", "1", "no-such-step", "--status", "done"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown step", r.stderr)

    def test_step_add_appends_and_is_idempotent(self):
        # ⑤ 判无后端时给 ⑥ 前端实现补测试步骤——step-add 追加 + 幂等
        self.run_ok(["step-add", "6", "unit-test", "单元测试"])
        self.run_ok(["step-add", "6", "integration-test", "集成测试"])
        s = read_state(self.dir)
        ph6 = next(p for p in s["phases"] if p["id"] == 6)
        ids = [x["id"] for x in ph6["steps"]]
        self.assertEqual(ids, ["scaffold", "frontend", "unit-test", "integration-test"])
        self.run_ok(["step-add", "6", "unit-test", "单元测试"])  # 幂等：不再追加
        ph6b = next(p for p in read_state(self.dir)["phases"] if p["id"] == 6)
        self.assertEqual([x["id"] for x in ph6b["steps"]], ids)

    def test_status_human_readable_contains_product(self):
        # status is NOT json — assert it prints product + phase counter
        r = self.run_ok(["status"])
        self.assertIn(self.PRODUCT, r.stdout)
        self.assertIn("phase 1/8", r.stdout)


class TestArtifactLog(PfStateBase):
    def _make_file(self, rel):
        full = os.path.join(self.dir, ".productflow", rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write("x")
        return rel

    def test_artifact_registered_with_inferred_type(self):
        rel = self._make_file("artifacts/phase-1/shot.png")
        r = self.run_ok(["artifact", "1", rel, "--title", "Shot"])
        self.assertEqual(r.stdout.strip(), f"registered {rel} (v1)")
        ph1 = next(p for p in read_state(self.dir)["phases"] if p["id"] == 1)
        self.assertEqual(len(ph1["artifacts"]), 1)
        a = ph1["artifacts"][0]
        self.assertEqual(a["file"], rel)
        self.assertEqual(a["title"], "Shot")
        self.assertEqual(a["type"], "image")  # .png -> image

    def test_artifact_explicit_type_overrides(self):
        rel = self._make_file("artifacts/phase-1/data.bin")
        self.run_ok(["artifact", "1", rel, "--title", "Bin", "--type", "weird"])
        ph1 = next(p for p in read_state(self.dir)["phases"] if p["id"] == 1)
        self.assertEqual(ph1["artifacts"][0]["type"], "weird")

    def test_artifact_reregister_dedupes_by_path(self):
        # 同路径重登记：去重（只留一条）+ 时间戳刷新（前端据此绕过浏览器缓存）
        rel = self._make_file("artifacts/phase-6/preview-home.png")
        self.run_ok(["artifact", "6", rel, "--title", "v1"])
        ts1 = next(p for p in read_state(self.dir)["phases"] if p["id"] == 6)["artifacts"][0]["ts"]
        self.run_ok(["artifact", "6", rel, "--title", "v2"])
        arts = next(p for p in read_state(self.dir)["phases"] if p["id"] == 6)["artifacts"]
        self.assertEqual(len(arts), 1)            # 没堆成两条
        self.assertEqual(arts[0]["title"], "v2")  # 留的是最新那条
        self.assertGreaterEqual(arts[0]["ts"], ts1)

    def test_artifact_version_tracks_phase_generation(self):
        # 版本 = 本阶段「第几代」：每次重做（phase→active）后登记的产物号 +1，老批留痕可对比。
        a = self._make_file("artifacts/phase-1/r1.md")
        self.run_ok(["phase", "1", "--status", "active"])          # 第 1 代
        r = self.run_ok(["artifact", "1", a, "--title", "竞品报告"])
        self.assertIn("(v1)", r.stdout)
        self.run_ok(["phase", "1", "--status", "done"])
        self.run_ok(["phase", "1", "--status", "active"])          # 重做 → 第 2 代
        b = self._make_file("artifacts/phase-1/r2.md")
        r = self.run_ok(["artifact", "1", b, "--title", "竞品矩阵"])
        self.assertIn("(v2)", r.stdout)
        c = self._make_file("artifacts/phase-1/r3.md")
        self.run_ok(["artifact", "1", c, "--title", "核心矛盾"])    # 同一代里再登记仍是 v2
        arts = next(p for p in read_state(self.dir)["phases"] if p["id"] == 1)["artifacts"]
        self.assertEqual({x["file"]: x["version"] for x in arts}, {a: 1, b: 2, c: 2})
        # active→active 不重复 +1（同一代内多次设 active 不抖版本号）
        self.run_ok(["phase", "1", "--status", "active"])
        d = self._make_file("artifacts/phase-1/r4.md")
        self.run_ok(["artifact", "1", d, "--title", "报告"])
        arts = next(p for p in read_state(self.dir)["phases"] if p["id"] == 1)["artifacts"]
        self.assertEqual(next(x for x in arts if x["file"] == d)["version"], 2)

    def test_artifact_rm_unregisters_and_deletes(self):
        rel = self._make_file("artifacts/phase-6/preview-home.png")
        self.run_ok(["artifact", "6", rel, "--title", "Shot"])
        full = os.path.join(self.dir, ".productflow", rel)
        self.assertTrue(os.path.exists(full))
        r = self.run_ok(["artifact-rm", "6", rel])
        self.assertIn("file deleted", r.stdout)
        ph6 = next(p for p in read_state(self.dir)["phases"] if p["id"] == 6)
        self.assertEqual(len(ph6["artifacts"]), 0)   # 撤销登记
        self.assertFalse(os.path.exists(full))       # 磁盘文件也删了

    def test_artifact_rm_keep_file(self):
        rel = self._make_file("artifacts/phase-6/keep.png")
        self.run_ok(["artifact", "6", rel, "--title", "Keep"])
        self.run_ok(["artifact-rm", "6", rel, "--keep-file"])
        ph6 = next(p for p in read_state(self.dir)["phases"] if p["id"] == 6)
        self.assertEqual(len(ph6["artifacts"]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.dir, ".productflow", rel)))  # 文件保留

    def test_artifact_mindmap_double_ext(self):
        # ".mm.md" is special-cased to type "mindmap" BEFORE the plain ".md"
        # extension lookup; a normal ".md" would otherwise infer "md".
        rel = self._make_file("artifacts/phase-1/flow.mm.md")
        self.run_ok(["artifact", "1", rel, "--title", "Mind"])
        ph1 = next(p for p in read_state(self.dir)["phases"] if p["id"] == 1)
        self.assertEqual(ph1["artifacts"][0]["type"], "mindmap")

    def test_artifact_dedup_same_file(self):
        rel = self._make_file("artifacts/phase-1/a.md")
        self.run_ok(["artifact", "1", rel, "--title", "First"])
        self.run_ok(["artifact", "1", rel, "--title", "Second"])
        ph1 = next(p for p in read_state(self.dir)["phases"] if p["id"] == 1)
        # same file replaced, not duplicated
        self.assertEqual(len(ph1["artifacts"]), 1)
        self.assertEqual(ph1["artifacts"][0]["title"], "Second")
        self.assertEqual(ph1["artifacts"][0]["type"], "md")

    def test_artifact_missing_file_fails(self):
        r = cli(["artifact", "1", "artifacts/phase-1/nope.png", "--title", "X"],
                self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("artifact file not found", r.stderr)

    def test_log_appends(self):
        before = len(read_state(self.dir)["log"])
        r = self.run_ok(["log", "hello log"])
        self.assertEqual(r.stdout.strip(), "logged")
        s = read_state(self.dir)
        self.assertEqual(len(s["log"]), before + 1)
        self.assertEqual(s["log"][-1]["msg"], "hello log")


class TestPages(PfStateBase):
    def _add(self, name, **kw):
        args = ["page", "add", name]
        for k, v in kw.items():
            args += [f"--{k}", v]
        r = self.run_ok(args)
        m = re.match(r"added page (pg-[0-9a-f]+):", r.stdout.strip())
        self.assertIsNotNone(m, r.stdout)
        return m.group(1)

    def test_add_creates_placeholder(self):
        pgid = self._add("登录页", group="认证")
        data = read_json_file(self.dir, "pages.json")
        self.assertEqual(len(data["pages"]), 1)
        p = data["pages"][0]
        self.assertEqual(p["id"], pgid)
        self.assertEqual(p["name"], "登录页")
        self.assertEqual(p["group"], "认证")
        self.assertEqual(p["status"], "placeholder")
        self.assertEqual(p["versions"], [])

    def test_add_default_group(self):
        self._add("首页")
        p = read_json_file(self.dir, "pages.json")["pages"][0]
        self.assertEqual(p["group"], "未分组")

    def test_list_output(self):
        pgid = self._add("详情页", group="商品")
        r = self.run_ok(["page", "list"])
        self.assertIn(pgid, r.stdout)
        self.assertIn("[placeholder]", r.stdout)
        self.assertIn("商品/详情页", r.stdout)

    def test_list_empty(self):
        r = self.run_ok(["page", "list"])
        self.assertEqual(r.stdout.strip(), "(no pages)")

    def test_rm_removes(self):
        pgid = self._add("临时页")
        r = self.run_ok(["page", "rm", pgid])
        self.assertEqual(r.stdout.strip(), f"removed page {pgid}")
        self.assertEqual(read_json_file(self.dir, "pages.json")["pages"], [])

    def test_rm_unknown_fails(self):
        r = cli(["page", "rm", "pg-deadbe"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("page not found", r.stderr)

    def test_set_add_version_auto_done(self):
        pgid = self._add("方案页")
        self.run_ok(["page", "set", pgid, "--add-version", "artifacts/phase-4/v1.png",
                     "--platform", "PC"])
        p = read_json_file(self.dir, "pages.json")["pages"][0]
        # placeholder -> done once a version is attached
        self.assertEqual(p["status"], "done")
        # versions 元素是 {file, platform}
        self.assertEqual(p["versions"],
                         [{"file": "artifacts/phase-4/v1.png", "platform": "PC"}])

    def test_set_add_version_per_platform(self):
        # 同一页不同平台 = 两个版本（"每页 × 平台"）
        pgid = self._add("方案页")
        self.run_ok(["page", "set", pgid, "--add-version", "pc.png", "--platform", "PC"])
        self.run_ok(["page", "set", pgid, "--add-version", "h5.png", "--platform", "H5"])
        p = read_json_file(self.dir, "pages.json")["pages"][0]
        self.assertEqual(len(p["versions"]), 2)
        self.assertEqual({v["platform"] for v in p["versions"]}, {"PC", "H5"})

    def test_set_add_version_dedups(self):
        pgid = self._add("方案页")
        self.run_ok(["page", "set", pgid, "--add-version", "v.png", "--platform", "PC"])
        self.run_ok(["page", "set", pgid, "--add-version", "v.png", "--platform", "PC"])
        p = read_json_file(self.dir, "pages.json")["pages"][0]
        self.assertEqual(p["versions"], [{"file": "v.png", "platform": "PC"}])

    def test_set_explicit_status_overrides_autodone(self):
        pgid = self._add("方案页")
        self.run_ok(["page", "set", pgid,
                     "--add-version", "v.png", "--status", "designing"])
        p = read_json_file(self.dir, "pages.json")["pages"][0]
        # explicit --status wins over auto-done
        self.assertEqual(p["status"], "designing")

    def test_set_name_group_note(self):
        pgid = self._add("旧名")
        self.run_ok(["page", "set", pgid, "--name", "新名",
                     "--group", "新组", "--note", "说明"])
        p = read_json_file(self.dir, "pages.json")["pages"][0]
        self.assertEqual(p["name"], "新名")
        self.assertEqual(p["group"], "新组")
        self.assertEqual(p["note"], "说明")


class TestExplore(PfStateBase):
    def test_show_default_structure(self):
        r = self.run_ok(["explore", "show"])
        e = json.loads(r.stdout)
        self.assertEqual(e["request"], {})   # 按 kind 分槽，默认空 dict
        self.assertEqual(e["refs"], [])
        self.assertEqual(e["heroes"], [])
        self.assertEqual(e["styleSummary"], "")
        self.assertEqual(e["selectedRefs"], [])

    def test_add_ref(self):
        self.run_ok(["explore", "add-ref", "artifacts/phase-2/refs/a.png",
                     "--title", "Ref A", "--source", "http://x"])
        e = read_json_file(self.dir, "explore.json")
        self.assertEqual(len(e["refs"]), 1)
        ref = e["refs"][0]
        self.assertEqual(ref["file"], "artifacts/phase-2/refs/a.png")
        self.assertEqual(ref["title"], "Ref A")
        self.assertEqual(ref["source"], "http://x")
        self.assertRegex(ref["id"], r"^ref-[0-9a-f]{6}$")

    def test_add_ref_dedup_same_source_or_file(self):
        # 第二/三轮找参考常抓回同样的热门结果——同来源 URL 或同文件路径都不重复登记
        self.run_ok(["explore", "add-ref", "artifacts/phase-2/refs/1.png",
                     "--title", "A", "--source", "https://dribbble.com/shots/111"])
        self.run_ok(["explore", "add-ref", "artifacts/phase-2/refs/2.png",   # 同来源·不同文件 → 跳过
                     "--title", "A again", "--source", "https://dribbble.com/shots/111"])
        self.run_ok(["explore", "add-ref", "artifacts/phase-2/refs/1.png", "--title", "dup file"])  # 同文件 → 跳过
        self.run_ok(["explore", "add-ref", "artifacts/phase-2/refs/3.png",   # 新来源 → 登记
                     "--title", "B", "--source", "https://dribbble.com/shots/222"])
        e = read_json_file(self.dir, "explore.json")
        self.assertEqual(len(e["refs"]), 2)
        self.assertCountEqual([r["source"] for r in e["refs"]],
                              ["https://dribbble.com/shots/111", "https://dribbble.com/shots/222"])

    def test_add_ref_empty_source_not_deduped(self):
        # 空来源不能被当成"重复"（否则所有无来源参考只能存一张）
        self.run_ok(["explore", "add-ref", "artifacts/phase-2/refs/a.png", "--title", "A"])
        self.run_ok(["explore", "add-ref", "artifacts/phase-2/refs/b.png", "--title", "B"])
        self.assertEqual(len(read_json_file(self.dir, "explore.json")["refs"]), 2)

    def test_add_hero(self):
        self.run_ok(["explore", "add-hero", "artifacts/phase-2/hero.png", "--style", "极简"])
        e = read_json_file(self.dir, "explore.json")
        self.assertEqual(len(e["heroes"]), 1)
        self.assertEqual(e["heroes"][0]["file"], "artifacts/phase-2/hero.png")
        self.assertEqual(e["heroes"][0]["style"], "极简")
        self.assertRegex(e["heroes"][0]["id"], r"^hero-[0-9a-f]{6}$")

    def test_gen_record_appends_for_dialog(self):
        # ③ 对话框数据：每次生成记录用了哪些参考 + 发了什么 prompt + 出了哪几张
        self.run_ok(["explore", "gen-record", "--mode", "gen", "--prompt", "P1",
                     "--refs", "a.png", "b.png", "--results", "01.png"])
        self.run_ok(["explore", "gen-record", "--mode", "edit", "--prompt", "P2",
                     "--refs", "01.png", "--results", "edit-01.png", "edit-02.png"])
        log = read_json_file(self.dir, "explore.json")["heroGenLog"]
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["mode"], "gen")
        self.assertEqual(log[0]["prompt"], "P1")
        self.assertEqual(log[0]["refs"], ["a.png", "b.png"])
        self.assertEqual(log[0]["results"], ["01.png"])
        self.assertIn("ts", log[0])
        self.assertEqual(log[1]["mode"], "edit")
        self.assertEqual(len(log[1]["results"]), 2)

    def test_set_summary(self):
        self.run_ok(["explore", "set-summary", "干净留白、克制配色"])
        self.assertEqual(read_json_file(self.dir, "explore.json")["styleSummary"],
                         "干净留白、克制配色")

    def test_select_refs_by_id(self):
        # CLI 选稿：select-refs 写 selectedRefs（按 ref id），不必手改 explore.json
        self.run_ok(["explore", "add-ref", "artifacts/phase-2/refs/a.png", "--title", "A"])
        self.run_ok(["explore", "add-ref", "artifacts/phase-2/refs/b.png", "--title", "B"])
        e = read_json_file(self.dir, "explore.json")
        ids = [r["id"] for r in e["refs"]]
        self.run_ok(["explore", "select-refs", ids[1], ids[0], ids[1]])   # 含重复 → 去重保序
        self.assertEqual(read_json_file(self.dir, "explore.json")["selectedRefs"], [ids[1], ids[0]])
        # 未知 id → 报错
        r = cli(["explore", "select-refs", "ref-nope"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)

    def test_select_hero_stores_file_path(self):
        # select-hero 收 hero id，落库为其 file 路径（与 server 约定一致）
        self.run_ok(["explore", "add-hero", "artifacts/phase-3/heroes/h.png", "--style", "深色"])
        hid = read_json_file(self.dir, "explore.json")["heroes"][0]["id"]
        self.run_ok(["explore", "select-hero", hid])
        self.assertEqual(read_json_file(self.dir, "explore.json")["selectedHero"],
                         "artifacts/phase-3/heroes/h.png")
        r = cli(["explore", "select-hero", "hero-nope"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)

    def test_done_request_clears_all(self):
        # request 是按 kind 分槽的 dict；无 --kind 清全部
        p = os.path.join(self.dir, ".productflow", "explore.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"request": {"search-refs": {"n": 6}, "gen-heroes": {"n": 2}}}, f)
        self.run_ok(["explore", "done-request"])
        self.assertEqual(read_json_file(self.dir, "explore.json")["request"], {})

    def test_done_request_clears_one_kind(self):
        # --kind 只清一类，另一阶段的请求保留（P2/P3 互不干扰）
        p = os.path.join(self.dir, ".productflow", "explore.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"request": {"search-refs": {"n": 6}, "gen-heroes": {"n": 2}}}, f)
        self.run_ok(["explore", "done-request", "--kind", "search-refs"])
        req = read_json_file(self.dir, "explore.json")["request"]
        self.assertNotIn("search-refs", req)
        self.assertIn("gen-heroes", req)

    def test_clear_resets(self):
        self.run_ok(["explore", "add-ref", "a.png"])
        self.run_ok(["explore", "set-summary", "x"])
        self.run_ok(["explore", "clear"])
        e = read_json_file(self.dir, "explore.json")
        self.assertEqual(e["refs"], [])
        self.assertEqual(e["styleSummary"], "")
        self.assertEqual(e["request"], {})

    def test_remove_ref_drops_entry_selection_and_file(self):
        rel = "artifacts/phase-2/refs/x.png"
        p = os.path.join(self.dir, ".productflow", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write("png")
        self.run_ok(["explore", "add-ref", rel])
        rid = read_json_file(self.dir, "explore.json")["refs"][0]["id"]
        # 模拟该 ref 被选中
        ep = os.path.join(self.dir, ".productflow", "explore.json")
        d = read_json_file(self.dir, "explore.json"); d["selectedRefs"] = [rid]
        with open(ep, "w") as f:
            json.dump(d, f)
        self.run_ok(["explore", "remove-ref", rid])
        e = read_json_file(self.dir, "explore.json")
        self.assertEqual(e["refs"], [])
        self.assertEqual(e["selectedRefs"], [])      # 选择里也清掉
        self.assertFalse(os.path.exists(p))           # 磁盘文件删

    def test_remove_hero_drops_entry_and_clears_base(self):
        rel = "artifacts/phase-3/heroes/h.png"
        p = os.path.join(self.dir, ".productflow", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write("png")
        self.run_ok(["explore", "add-hero", rel])
        hid = read_json_file(self.dir, "explore.json")["heroes"][0]["id"]
        ep = os.path.join(self.dir, ".productflow", "explore.json")
        d = read_json_file(self.dir, "explore.json"); d["selectedHero"] = rel
        with open(ep, "w") as f:
            json.dump(d, f)
        self.run_ok(["explore", "remove-hero", hid])
        e = read_json_file(self.dir, "explore.json")
        self.assertEqual(e["heroes"], [])
        self.assertEqual(e["selectedHero"], "")       # 基调也清掉
        self.assertFalse(os.path.exists(p))


class TestBrief(PfStateBase):
    def test_show_default(self):
        r = self.run_ok(["brief", "show"])
        b = json.loads(r.stdout)
        self.assertEqual(b["ready"], False)
        self.assertIsNone(b["request"])
        self.assertEqual(b["summary"],
                         {"goal": "", "users": "", "need": "", "scope": ""})

    def test_set_summary_sets_ready_and_clears_request(self):
        p = os.path.join(self.dir, ".productflow", "brief.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"request": {"kind": "summary"}, "ready": False}, f)
        self.run_ok(["brief", "set-summary",
                     "--goal", "G", "--users", "U", "--need", "N", "--scope", "S"])
        b = read_json_file(self.dir, "brief.json")
        self.assertEqual(b["ready"], True)
        self.assertIsNone(b["request"])
        self.assertEqual(b["summary"],
                         {"goal": "G", "users": "U", "need": "N", "scope": "S"})

    def test_set_summary_partial_fields_default_empty(self):
        self.run_ok(["brief", "set-summary", "--goal", "只设目标"])
        b = read_json_file(self.dir, "brief.json")
        self.assertEqual(b["summary"]["goal"], "只设目标")
        self.assertEqual(b["summary"]["users"], "")
        self.assertEqual(b["summary"]["need"], "")
        self.assertEqual(b["summary"]["scope"], "")
        self.assertTrue(b["ready"])

    def test_done_request_clears_without_ready(self):
        p = os.path.join(self.dir, ".productflow", "brief.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"request": {"kind": "summary"}, "ready": False}, f)
        self.run_ok(["brief", "done-request"])
        b = read_json_file(self.dir, "brief.json")
        self.assertIsNone(b["request"])
        # done-request alone does not flip ready
        self.assertEqual(b["ready"], False)


class TestInboxReply(PfStateBase):
    def _append(self, obj):
        p = os.path.join(self.dir, ".productflow", "inbox.jsonl")
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def test_empty_inbox(self):
        r = self.run_ok(["inbox"])
        self.assertEqual(r.stdout.strip(), "(inbox empty)")

    def test_reads_web_then_advances(self):
        self._append({"ts": "2026-01-01 00:00:00", "from": "web", "text": "hi"})
        r1 = self.run_ok(["inbox"])
        self.assertIn("hi", r1.stdout)
        # cursor advanced -> second read is "no new messages"
        r2 = self.run_ok(["inbox"])
        self.assertEqual(r2.stdout.strip(), "(no new messages)")

    def test_only_web_messages_shown(self):
        self._append({"ts": "t", "from": "agent", "text": "agent-line"})
        self._append({"ts": "t", "from": "web", "text": "web-line"})
        r = self.run_ok(["inbox"])
        self.assertIn("web-line", r.stdout)
        self.assertNotIn("agent-line", r.stdout)

    def test_cursor_advances_to_total_lines(self):
        self._append({"ts": "t", "from": "agent", "text": "a"})
        self._append({"ts": "t", "from": "web", "text": "w"})
        self.run_ok(["inbox"])
        with open(os.path.join(self.dir, ".productflow", "inbox.cursor")) as f:
            self.assertEqual(f.read().strip(), "2")

    def test_peek_does_not_advance(self):
        self._append({"ts": "t", "from": "web", "text": "peekme"})
        r1 = self.run_ok(["inbox", "--peek"])
        self.assertIn("peekme", r1.stdout)
        # no cursor file written
        self.assertFalse(os.path.exists(
            os.path.join(self.dir, ".productflow", "inbox.cursor")))
        # still unread on next peek
        r2 = self.run_ok(["inbox", "--peek"])
        self.assertIn("peekme", r2.stdout)

    def test_reply_appends_agent_line(self):
        r = self.run_ok(["reply", "答复内容"])
        self.assertEqual(r.stdout.strip(), "replied")
        p = os.path.join(self.dir, ".productflow", "inbox.jsonl")
        with open(p, encoding="utf-8") as f:
            lines = [json.loads(x) for x in f if x.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["from"], "agent")
        self.assertEqual(lines[0]["text"], "答复内容")

    def test_reply_then_inbox_ignores_agent(self):
        self.run_ok(["reply", "agent says"])
        r = self.run_ok(["inbox"])
        # only agent line present -> no web unread
        self.assertEqual(r.stdout.strip(), "(no new messages)")


class TestUnregister(PfStateBase):
    def _reg(self, pid):
        return os.path.join(self.home, ".productflow", "projects", pid + ".json")

    def test_unregister_removes_entry_keeps_files(self):
        self.assertTrue(os.path.isfile(self._reg(self.pid)))
        r = cli(["unregister", self.pid], self.home, project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("unregistered", r.stdout)
        # registry entry gone
        self.assertFalse(os.path.exists(self._reg(self.pid)))
        # project files untouched
        self.assertTrue(os.path.isfile(
            os.path.join(self.dir, ".productflow", "state.json")))

    def test_unregister_missing_fails(self):
        r = cli(["unregister", "ghost-0000"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no registry entry", r.stderr)

    def test_unregister_invalid_id_fails(self):
        r = cli(["unregister", "BadID!!"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid project id", r.stderr)


class TestDirResolution(unittest.TestCase):
    """--dir default comes from $PF_PROJECT; helpers.cli passes it via project=."""

    def setUp(self):
        self.home = make_home()
        self.dir = os.path.join(self.home, "code", "envproj")
        os.makedirs(self.dir, exist_ok=True)
        r = cli(["init", "--product", "Env Project"], self.home, project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)

    def tearDown(self):
        rm_home(self.home)

    def test_pf_project_env_used_without_dir_flag(self):
        # project= sets PF_PROJECT; no --dir flag -> command resolves to that dir
        r = cli(["log", "via PF_PROJECT"], self.home, project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        s = read_state(self.dir)
        self.assertEqual(s["log"][-1]["msg"], "via PF_PROJECT")

    def test_explicit_dir_flag_beats_env(self):
        # second project; point PF_PROJECT at dir1 but --dir at dir2
        dir2 = os.path.join(self.home, "code", "envproj2")
        os.makedirs(dir2, exist_ok=True)
        cli(["init", "--product", "Second"], self.home, project=dir2)
        r = cli(["--dir", dir2, "log", "into dir2"], self.home, project=self.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(read_state(dir2)["log"][-1]["msg"], "into dir2")
        # dir1 (PF_PROJECT) untouched by this command
        self.assertNotEqual(read_state(self.dir)["log"][-1]["msg"], "into dir2")

    def test_command_on_uninitialized_dir_fails(self):
        empty = os.path.join(self.home, "code", "noinit")
        os.makedirs(empty, exist_ok=True)
        r = cli(["status"], self.home, project=empty)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("run init first", r.stderr)


class TestMeta(PfStateBase):
    """`meta --product` renames the display name without touching id/dir."""

    def test_meta_product_updates_display_name(self):
        before = read_state(self.dir)
        self.run_ok(["meta", "--product", "新的显示名"])
        after = read_state(self.dir)
        self.assertEqual(after["product"], "新的显示名")
        # id / project_dir unchanged — registry keys are stable
        self.assertEqual(after["id"], before["id"])
        self.assertEqual(after["project_dir"], before["project_dir"])

    def test_meta_empty_product_falls_back(self):
        self.run_ok(["meta", "--product", "   "])
        self.assertEqual(read_state(self.dir)["product"], "未命名项目")

    def test_meta_noop_without_product(self):
        before = read_state(self.dir)["product"]
        self.run_ok(["meta"])
        self.assertEqual(read_state(self.dir)["product"], before)


class TestChoice(PfStateBase):
    """通用选项确认：agent ask → 用户/CLI answer → agent show 读 answer。"""

    def test_ask_creates_pending_choice_and_inbox(self):
        r = self.run_ok(["choice", "ask", "--stage", "5", "--question", "选哪个模板？",
                         "--option", "T1", "--option", "T2"])
        cid = r.stdout.strip()
        self.assertRegex(cid, r"^ch-[0-9a-f]{6}$")
        ch = read_json_file(self.dir, "choices.json")["choices"][0]
        self.assertEqual(ch["question"], "选哪个模板？")
        self.assertEqual(ch["options"], ["T1", "T2"])
        self.assertIsNone(ch["answer"])
        self.assertEqual(ch["stage"], 5)
        # 抛问会投一条 inbox（type=choice）
        ip = os.path.join(self.dir, ".productflow", "inbox.jsonl")
        with open(ip, encoding="utf-8") as f:
            inbox = [json.loads(line) for line in f if line.strip()]
        self.assertTrue(any(m.get("type") == "choice" for m in inbox))

    def test_answer_then_show(self):
        cid = self.run_ok(["choice", "ask", "--question", "A 还是 B？",
                           "--option", "A", "--option", "B"]).stdout.strip()
        self.run_ok(["choice", "answer", cid, "--text", "A"])
        r = self.run_ok(["choice", "show"])
        c = json.loads(r.stdout)
        self.assertEqual(c["choices"][0]["answer"], "A")

    def test_wait_returns_answer_when_already_answered(self):
        cid = self.run_ok(["choice", "ask", "--question", "选?", "--option", "A", "--option", "B"]).stdout.strip()
        self.run_ok(["choice", "answer", cid, "--text", "B"])
        r = self.run_ok(["choice", "wait", cid, "--timeout", "5"])   # 已答复 → 立即返回
        c = json.loads(r.stdout)
        self.assertEqual(c["answer"], "B")
        self.assertNotIn("timeout", c)

    def test_wait_times_out_with_null_answer(self):
        cid = self.run_ok(["choice", "ask", "--question", "选?", "--option", "A"]).stdout.strip()
        r = self.run_ok(["choice", "wait", cid, "--timeout", "1"])   # 没人答 → ~1s 后超时返回
        c = json.loads(r.stdout)
        self.assertTrue(c.get("timeout"))
        self.assertIsNone(c.get("answer"))


class TestBackendFlow(PfStateBase):
    """backend-flow.json 薄关系层 CLI：节点/边/页面链接/状态/入口。"""

    def bf(self):
        return read_json_file(self.dir, "backend-flow.json")

    def test_add_nodes_edges_links_status_entry(self):
        self.run_ok(["backend-flow", "add-node", "--id", "module:auth", "--type", "module"])
        self.run_ok(["backend-flow", "add-node", "--id", "api:login", "--type", "interface", "--module", "module:auth"])
        self.run_ok(["backend-flow", "add-node", "--id", "table:users", "--type", "table"])
        self.run_ok(["backend-flow", "add-edge", "--from", "api:login", "--to", "table:users", "--type", "writes_to"])
        self.run_ok(["backend-flow", "link-page", "--page", "page:login", "--module", "module:auth"])
        self.run_ok(["backend-flow", "set-status", "--id", "module:auth", "--status", "doing"])
        self.run_ok(["backend-flow", "set-entry", "--id", "module:auth"])
        bf = self.bf()
        ids = {n["id"]: n for n in bf["nodes"]}
        self.assertEqual(set(ids), {"module:auth", "api:login", "table:users"})
        self.assertEqual(ids["module:auth"]["status"], "doing")
        self.assertEqual(ids["api:login"]["module"], "module:auth")
        self.assertEqual(ids["api:login"]["status"], "todo")  # 默认 todo
        self.assertEqual(bf["edges"], [{"from": "api:login", "to": "table:users", "type": "writes_to", "label": ""}])
        self.assertEqual(bf["pageLinks"], [{"page": "page:login", "module": "module:auth"}])
        self.assertEqual(bf["entry"], "module:auth")

    def test_add_node_is_idempotent_update(self):
        self.run_ok(["backend-flow", "add-node", "--id", "module:x", "--type", "module"])
        self.run_ok(["backend-flow", "add-node", "--id", "module:x", "--type", "module", "--status", "done"])
        bf = self.bf()
        self.assertEqual(len(bf["nodes"]), 1)          # 同 id 更新、不重复
        self.assertEqual(bf["nodes"][0]["status"], "done")

    def test_add_node_with_name_and_fields(self):
        self.run_ok(["backend-flow", "add-node", "--id", "table:users", "--type", "table", "--name", "用户表",
                     "--field", "id INTEGER PK", "--field", "email TEXT UNIQUE"])
        n = self.bf()["nodes"][0]
        self.assertEqual(n["name"], "用户表")   # 中文显示名
        self.assertEqual(n["fields"], ["id INTEGER PK", "email TEXT UNIQUE"])

    def test_proc_on_off(self):
        self.run_ok(["backend-flow", "add-node", "--id", "module:x", "--type", "module"])
        self.run_ok(["backend-flow", "proc", "--id", "module:x", "--state", "on"])
        self.assertTrue(self.bf()["nodes"][0].get("proc"))     # 处理中标记
        self.run_ok(["backend-flow", "proc", "--id", "module:x", "--state", "off"])
        self.assertNotIn("proc", self.bf()["nodes"][0])        # 清除

    def test_edge_dedup_and_rm(self):
        for _ in range(2):
            self.run_ok(["backend-flow", "add-edge", "--from", "a", "--to", "b", "--type", "calls"])
        self.assertEqual(len(self.bf()["edges"]), 1)   # 去重
        self.run_ok(["backend-flow", "rm-edge", "--from", "a", "--to", "b"])
        self.assertEqual(self.bf()["edges"], [])

    def test_rm_node_cascades_edges_and_links(self):
        self.run_ok(["backend-flow", "add-node", "--id", "module:auth", "--type", "module"])
        self.run_ok(["backend-flow", "add-edge", "--from", "module:auth", "--to", "table:t", "--type", "reads_from"])
        self.run_ok(["backend-flow", "link-page", "--page", "p1", "--module", "module:auth"])
        self.run_ok(["backend-flow", "rm-node", "--id", "module:auth"])
        bf = self.bf()
        self.assertEqual(bf["nodes"], [])
        self.assertEqual(bf["edges"], [])              # 连带删边
        self.assertEqual(bf["pageLinks"], [])          # 连带删页面链接

    def test_set_status_unknown_node_fails(self):
        r = cli(["backend-flow", "set-status", "--id", "nope", "--status", "done"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)

    def test_bad_type_rejected(self):
        r = cli(["backend-flow", "add-node", "--id", "x", "--type", "widget"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)           # choices=module/interface/table

    def test_clear_and_show(self):
        self.run_ok(["backend-flow", "add-node", "--id", "m", "--type", "module"])
        self.run_ok(["backend-flow", "clear"])
        bf = json.loads(self.run_ok(["backend-flow", "show"]).stdout)
        self.assertEqual(bf["nodes"], [])
        self.assertEqual(bf["edges"], [])
        self.assertIsNone(bf["entry"])


class TestProductKey(PfStateBase):
    """产品级第三方 key 需求 CLI（product-keys.json；值另存 secrets、不在此）。"""
    def _pk(self):
        return read_json_file(self.dir, "product-keys.json")

    def test_add_and_fields(self):
        self.run_ok(["product-key", "add", "--key", "STRIPE_SECRET_KEY", "--desc", "Stripe 支付", "--module", "payment"])
        keys = self._pk()["keys"]
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["key"], "STRIPE_SECRET_KEY")
        self.assertEqual(keys[0]["desc"], "Stripe 支付")
        self.assertEqual(keys[0]["module"], "payment")

    def test_add_dedups_by_key_updates_desc(self):
        self.run_ok(["product-key", "add", "--key", "K", "--desc", "old"])
        self.run_ok(["product-key", "add", "--key", "K", "--desc", "new"])
        keys = self._pk()["keys"]
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["desc"], "new")

    def test_rm(self):
        self.run_ok(["product-key", "add", "--key", "A"])
        self.run_ok(["product-key", "add", "--key", "B"])
        self.run_ok(["product-key", "rm", "--key", "A"])
        self.assertEqual([k["key"] for k in self._pk()["keys"]], ["B"])

    def test_clear(self):
        self.run_ok(["product-key", "add", "--key", "A"])
        self.run_ok(["product-key", "clear"])
        self.assertEqual(self._pk()["keys"], [])


class TestArch(PfStateBase):
    """④ 业务架构树：arch.json → `arch build` 确定性组装——图标由树中深度、父子由 parent 字段。"""

    def _write_arch(self, data):
        with open(os.path.join(self.dir, ".productflow", "arch.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def test_arch_build_icons_and_nesting(self):
        self._write_arch({"product": "Wise App", "pages": [
            {"id": "home", "name": "首页", "parent": None,
             "modules": [{"name": "快捷操作", "features": ["Send", "Add"]}]},
            {"id": "acct", "name": "币种账户详情", "parent": "home", "modules": []},
            {"id": "quote", "name": "转账报价页", "parent": "home", "modules": []},
            {"id": "confirm", "name": "转账确认页", "parent": "quote", "modules": []},
            {"id": "me", "name": "我的", "parent": None, "modules": []},
        ]})
        self.run_ok(["arch", "build"])
        mm = os.path.join(self.dir, ".productflow", "artifacts", "phase-4", "module-arch.mm.md")
        self.assertTrue(os.path.isfile(mm))
        md = open(mm, encoding="utf-8").read()
        self.assertIn("## 🗂 首页", md)           # 顶层页 = 🗂 + ##
        self.assertIn("## 🗂 我的", md)
        self.assertIn("### 📄 币种账户详情", md)   # home 的子页 → 深一级 + 📄
        self.assertIn("### 📄 转账报价页", md)
        self.assertIn("#### 📄 转账确认页", md)     # quote 的子页 → 再深一级（父子嵌套生效）
        self.assertIn("- 🧩 快捷操作", md)          # 模块 = 🧩
        self.assertIn("  - Send", md)               # 功能点 = 缩进列表
        self.assertIn("业务模块架构", json.dumps(read_state(self.dir), ensure_ascii=False))  # 已登记

    def test_arch_build_dangling_parent_lifts_to_top(self):
        # 父 id 指向不存在的页 → 提到顶层（不丢节点、不成环）
        self._write_arch({"product": "P", "pages": [
            {"id": "a", "name": "A页", "parent": "ghost", "modules": []},
        ]})
        self.run_ok(["arch", "build"])
        md = open(os.path.join(self.dir, ".productflow", "artifacts", "phase-4", "module-arch.mm.md"), encoding="utf-8").read()
        self.assertIn("## 🗂 A页", md)

    def test_arch_build_missing_json_errors(self):
        r = cli(["arch", "build"], self.home, project=self.dir)
        self.assertNotEqual(r.returncode, 0)        # 无 arch.json → 非 0 退出（不静默）


class TestSpec(PfStateBase):
    def test_set_and_show_roundtrip(self):
        self.run_ok(["spec", "set-lib", "--platform", "PC", "--lib", "shadcn/ui + tailwind", "--theme", "neutral"])
        self.run_ok(["spec", "set-token", "color.blue.500", "--value", "#3498db", "--type", "color"])
        self.run_ok(["spec", "set-token", "color.action.primary", "--value", "color.blue.500", "--type", "color", "--ref"])
        spec = read_json_file(self.dir, "design-spec.json")
        self.assertEqual(spec["componentLib"]["PC"]["lib"], "shadcn/ui + tailwind")
        self.assertEqual(spec["tokens"]["color"]["blue"]["500"]["$value"], "#3498db")
        self.assertEqual(spec["tokens"]["color"]["action"]["primary"]["$value"], "{color.blue.500}")

    def test_set_page_component_state_asset(self):
        r = self.run_ok(["page", "add", "首页"])
        pgid = re.search(r"pg-[0-9a-f]+", r.stdout).group(0)
        self.run_ok(["spec", "set-page", pgid, "--type", "product",
                     "--component", "hero.cta:Button:primary",
                     "--state", "list:default,empty,loading",
                     "--asset", "hero.bg:gpt-image:x.png"])
        pg = read_json_file(self.dir, "design-spec.json")["pages"][0]
        self.assertEqual(pg["id"], pgid)
        self.assertEqual(pg["type"], "product")
        self.assertEqual(pg["components"][0], {"slot": "hero.cta", "lib": "Button", "variant": "primary"})
        self.assertEqual(pg["states"]["list"], ["default", "empty", "loading"])
        self.assertEqual(pg["assets"][0], {"slot": "hero.bg", "gen": "gpt-image", "file": "x.png"})

    def test_check_pass(self):
        r = self.run_ok(["page", "add", "首页"])
        pgid = re.search(r"pg-[0-9a-f]+", r.stdout).group(0)
        self.run_ok(["spec", "set-lib", "--platform", "PC", "--lib", "shadcn"])
        self.run_ok(["spec", "set-token", "color.blue.500", "--value", "#3498db", "--type", "color"])
        self.run_ok(["spec", "set-page", pgid, "--type", "product"])
        r = cli(["spec", "check"], self.home, project=self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_check_dangling_alias_fails(self):
        self.run_ok(["spec", "set-lib", "--platform", "PC", "--lib", "shadcn"])
        self.run_ok(["spec", "set-token", "color.bad", "--value", "nope.token", "--type", "color", "--ref"])
        r = cli(["spec", "check"], self.home, project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("悬空 alias", r.stdout)

    def test_check_page_id_mismatch_fails(self):
        self.run_ok(["spec", "set-lib", "--platform", "PC", "--lib", "shadcn"])
        self.run_ok(["spec", "set-page", "pg-nonexist", "--type", "product"])
        r = cli(["spec", "check"], self.home, project=self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("pages.json 不存在", r.stdout)

    def test_compile_writes_three_ends(self):
        self.run_ok(["spec", "set-token", "color.blue.500", "--value", "#3498db", "--type", "color"])
        self.run_ok(["spec", "compile", "--platform", "all", "--out", "artifacts/phase-6/tokens"])
        base = os.path.join(self.dir, ".productflow", "artifacts", "phase-6", "tokens")
        for fn in ("tokens.css", "Tokens.swift", "Tokens.kt"):
            self.assertTrue(os.path.isfile(os.path.join(base, fn)), fn)
        self.assertIn("--color-blue-500: #3498db;", open(os.path.join(base, "tokens.css")).read())

    def test_set_tokens_merge(self):
        import json as _json
        p1 = os.path.join(self.dir, "draft1.json")
        with open(p1, "w", encoding="utf-8") as f:
            _json.dump({"tokens": {"color": {"blue": {"500": {"$value": "#3498db", "$type": "color"}}},
                                   "space": {"4": {"$value": "16px", "$type": "dimension"}}}}, f)
        self.run_ok(["spec", "set-tokens", "--file", p1])
        p2 = os.path.join(self.dir, "draft2.json")
        with open(p2, "w", encoding="utf-8") as f:
            _json.dump({"radius": {"md": {"$value": "8px", "$type": "dimension"}}}, f)  # 直接子树，无 tokens 包裹
        self.run_ok(["spec", "set-tokens", "--file", p2])
        tk = read_json_file(self.dir, "design-spec.json")["tokens"]
        self.assertEqual(tk["color"]["blue"]["500"]["$value"], "#3498db")
        self.assertEqual(tk["space"]["4"]["$value"], "16px")
        self.assertEqual(tk["radius"]["md"]["$value"], "8px")  # 深合并保留了前面的

    def test_check_data_container_missing_state(self):
        r = self.run_ok(["page", "add", "列表页"])
        pgid = re.search(r"pg-[0-9a-f]+", r.stdout).group(0)
        self.run_ok(["spec", "set-lib", "--platform", "PC", "--lib", "shadcn"])
        self.run_ok(["spec", "set-page", pgid, "--type", "product", "--component", "feed:List:default"])
        # 无 --strict：数据容器缺 empty/loading 只是警告，exit 0
        r = cli(["spec", "check"], self.home, project=self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("数据容器", r.stdout)
        # --strict：警告升 error，exit 1
        r = cli(["spec", "check", "--strict"], self.home, project=self.dir)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
