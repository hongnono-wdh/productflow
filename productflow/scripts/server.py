#!/usr/bin/env python3
"""ProductFlow global console server. Serves all registered projects from ~/.productflow/."""

import argparse
import datetime as _dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_version() -> str:
    """版本号唯一来源：skill 根目录的 VERSION 文件（自动更新 / 版本检测都以它为准）。"""
    try:
        with open(os.path.join(SKILL_DIR, "VERSION"), encoding="utf-8") as f:
            return f.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"


VERSION = _read_version()

# ── 自动更新：以 GitHub 仓库的 VERSION 为远端版本来源 ──
UPDATE_REPO = "hongnono-wdh/productflow"
UPDATE_BRANCH = "main"
_REMOTE_VERSION_URL = f"https://raw.githubusercontent.com/{UPDATE_REPO}/{UPDATE_BRANCH}/productflow/VERSION"
_latest_version = None   # 启动后台拉一次；/api/update-check 用它


def _version_tuple(v):
    try:
        return tuple(int(x) for x in str(v).strip().split("."))
    except (ValueError, AttributeError):
        return (0,)


def _fetch_remote_version(timeout=4):
    try:
        with urllib.request.urlopen(_REMOTE_VERSION_URL, timeout=timeout) as r:
            return r.read().decode().strip() or None
    except Exception:  # noqa: BLE001  网络不通就当没新版本，不报错
        return None


def _refresh_latest():
    global _latest_version
    _latest_version = _fetch_remote_version()
    return _latest_version


def _repo_root():
    """skill 所在 git 仓库根目录（自动更新在这里 git pull）。非 git 克隆装的返回 None。"""
    try:
        r = subprocess.run(["git", "-C", os.path.realpath(SKILL_DIR), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 让 import pf_state 可用（同目录）
import pf_state  # noqa: E402  复用 create_project / _slug
CONSOLE_HTML = os.path.join(SKILL_DIR, "assets", "console.html")
PF_HOME = os.path.expanduser("~/.productflow")
PROJECTS_DIR = os.path.join(PF_HOME, "projects")
PENDING_DIR = os.path.join(PF_HOME, "pending")
# 部署凭证存这里——**项目仓库外**（项目的 .productflow/ 在产品 git 仓库里，凭证放那会跟着提交泄露）。
# 每项目一个 <id>.env（export K=V），目录 700 / 文件 600，仅本机可读、不进 git/留言。
SECRETS_DIR = os.path.join(PF_HOME, "secrets")
CRED_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ID_RE = re.compile(r"^[a-z0-9-]{1,64}$")
P_ROUTE = re.compile(r"^/p/([a-z0-9-]{1,64})(/.*)?$")
ALLOWED_HOSTS = ("127.0.0.1", "localhost")


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _atomic_write_json(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def _clip(s, n: int = 60) -> str:
    """把任意值转成单行字符串并截断到 n 字（供 agent-log 人话用）。"""
    s = "" if s is None else str(s)
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + "…"


def _agent_log_path(pf: str, phase: str) -> str:
    """每个阶段/请求一份进度文件：agent-log-<phase>.jsonl。
    避免 P1 brief / P2 找参考 / P3 首图 的后台 claude 进度互相 truncate 串台。"""
    safe = re.sub(r"[^a-z0-9-]+", "-", str(phase or "x").lower()).strip("-") or "x"
    return os.path.join(pf, f"agent-log-{safe}.jsonl")


def _log_line(pf: str, phase: str, kind: str, text: str) -> None:
    """往该阶段的 agent-log append 一条进度。失败静默（日志不该拖垮主流程）。"""
    try:
        with open(_agent_log_path(pf, phase), "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _now(), "phase": phase, "kind": kind, "text": text},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


def _log_reset(pf: str, phase: str, text: str) -> None:
    """请求开始：truncate 该阶段的 agent-log 并写一条 start（只清自己这阶段，不动别的）。"""
    try:
        os.makedirs(pf, exist_ok=True)
        with open(_agent_log_path(pf, phase), "w", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _now(), "phase": phase, "kind": "start", "text": text},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


def _distill_event(pf: str, phase: str, evt: dict) -> None:
    """把一行 claude stream-json 事件提炼成人话写进 agent-log。"""
    etype = evt.get("type")
    if etype == "assistant":
        for block in (evt.get("message") or {}).get("content") or []:
            btype = block.get("type")
            if btype == "text":
                txt = (block.get("text") or "").strip()
                if txt:
                    _log_line(pf, phase, "text", "💬 " + _clip(txt))
            elif btype == "tool_use":
                name = block.get("name") or "tool"
                inp = block.get("input") or {}
                # 取一点 input 摘要：优先常见字段，否则整体 json
                summary = (inp.get("command") or inp.get("description")
                           or inp.get("file_path") or inp.get("url") or inp.get("query"))
                if summary is None:
                    summary = json.dumps(inp, ensure_ascii=False) if inp else ""
                _log_line(pf, phase, "tool", f"🔧 调用 {name}: {_clip(summary)}")
    elif etype == "result":
        if evt.get("subtype") == "success":
            _log_line(pf, phase, "done", "✅ 完成")
        else:
            _log_line(pf, phase, "error", "❌ " + _clip(evt.get("subtype") or "失败"))


def _run_claude_streaming(pf: str, phase: str, prompt: str, cwd: str,
                          env: dict | None = None, timeout: int = 600) -> str:
    """用 Popen 跑 claude -p stream-json，逐行解析进度写进 agent-log，返回完整 result 文本。
    超时/异常时写 error 并返回已收集的文本。"""
    cmd = ["claude", "-p", prompt, "--dangerously-skip-permissions",
           "--output-format", "stream-json", "--verbose"]
    result_text = ""
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, bufsize=1)
    except (FileNotFoundError, OSError) as e:
        _log_line(pf, phase, "error", "❌ 启动 claude 失败: " + _clip(e, 80))
        return result_text
    deadline = time.monotonic() + timeout
    try:
        for line in proc.stdout:
            if time.monotonic() > deadline:
                proc.kill()
                _log_line(pf, phase, "error", "❌ 超时终止")
                break
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(evt, dict):
                continue
            if evt.get("type") == "result" and isinstance(evt.get("result"), str):
                result_text = evt["result"]
            _distill_event(pf, phase, evt)
        proc.wait(timeout=max(1, int(deadline - time.monotonic())))
    except subprocess.TimeoutExpired:
        proc.kill()
        _log_line(pf, phase, "error", "❌ 超时终止")
    except Exception as e:  # noqa: BLE001  流式读不该让整个线程崩
        _log_line(pf, phase, "error", "❌ 异常: " + _clip(e, 80))
    return result_text


def _clear_brief_request(pf: str) -> None:
    """清掉 brief.json 卡住的 request 槽——失败退出时调用，避免前端「生成中」一直转。"""
    try:
        bp = os.path.join(pf, "brief.json")
        br = _read_json(bp)
        if br.get("request") is not None:
            br["request"] = None
            _atomic_write_json(bp, br)
    except Exception:  # noqa: BLE001
        pass


def _auto_gen_brief(pf: str, description: str) -> None:
    """后台用本地 claude -p 把产品描述提炼成四字段摘要并回填 brief.json。
    失败（claude 不在/超时/解析失败）会清掉 request 槽（前端停转、可重试），inbox 里的 brief-request 仍在可降级接单。"""
    project_root = os.path.dirname(pf)
    prompt = (
        "你是产品分析助手。下面是用户对一个待做产品的描述——可能只是一句话，"
        "也可能是「用户原始提问 + 多轮澄清（问题澄清N / 用户选择 / 用户澄清N）」累积起来的对话，"
        "请综合全部信息理解；**已经澄清过的点不要再问**。\n"
        "输出：①四字段理解摘要 ②若仍有影响产品形态的歧义，列出待确认问题（每条给 2-4 个具体可选项，方便用户点选）。\n"
        "summary：goal=核心目标，users=目标用户，need=真实痛点/需求，scope=本次落地页范围边界——按当前信息给最合理判断（不要写「需确认」，把不确定的点放到 questions 里）。\n"
        "questions：只针对真正影响产品形态/方向的歧义点，每条 {q:问题, options:[2-4个具体选项]}，选项要具体可直接选；信息足够时 questions 为 []。\n"
        "只输出一个 JSON，不要解释、不要 markdown 代码块：\n"
        '{"goal":"...","users":"...","need":"...","scope":"...","questions":[{"q":"产品形态是？","options":["网页支付应用","支付营销落地页"]}]}\n\n'
        "产品描述：" + description
    )
    _log_reset(pf, "brief", "开始生成产品理解摘要")
    out_text = _run_claude_streaming(pf, "brief", prompt, project_root, timeout=180)
    m = re.search(r"\{.*\}", (out_text or "").strip(), re.S)
    if not m:
        _log_line(pf, "brief", "error", "❌ 无法从输出解析 JSON")
        print(f"[brief] 无法从 claude 输出解析 JSON: {(out_text or '')[:200]}", file=sys.stderr)
        _clear_brief_request(pf)
        return
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        _log_line(pf, "brief", "error", "❌ JSON 解析失败")
        print(f"[brief] JSON 解析失败: {e}", file=sys.stderr)
        _clear_brief_request(pf)
        return
    br_path = os.path.join(pf, "brief.json")
    try:
        with open(br_path, encoding="utf-8") as f:
            br = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        br = {"description": description, "request": None, "summary": {}, "ready": False}
    br["summary"] = {k: str(obj.get(k, "")) for k in ("goal", "users", "need", "scope")}
    questions = []
    for q in (obj.get("questions") or [])[:6]:
        if isinstance(q, dict) and str(q.get("q", "")).strip():
            opts = [str(o).strip() for o in (q.get("options") or []) if str(o).strip()][:4]
            questions.append({"q": str(q["q"]).strip(), "options": opts})
    br["questions"] = questions
    br["request"] = None
    br["ready"] = True
    br["confirmed"] = False   # 新生成的摘要（可能带新问题）→ 重置确认态，等用户确认
    _atomic_write_json(br_path, br)
    print(f"[brief] 自动生成摘要完成 → {br_path}", file=sys.stderr)


def _inject_openai_env(env: dict) -> None:
    """从 ~/.config/openai/env 读 export KEY=VAL 注入 env（openai-image-gen 生图需要 key/base_url）。"""
    try:
        with open(os.path.expanduser("~/.config/openai/env"), encoding="utf-8") as f:
            for line in f:
                m = re.match(r'\s*export\s+(\w+)\s*=\s*"?([^"\n]*)"?', line)
                if m:
                    env[m.group(1)] = m.group(2)
    except OSError:
        pass


def _secrets_path(pid: str) -> str:
    return os.path.join(SECRETS_DIR, pid + ".env")


def _load_deploy_creds(pid: str) -> dict:
    """读某项目的部署凭证（export K=V → {K:V}）。文件不存在/非法 id → {}。"""
    if not ID_RE.match(pid or ""):
        return {}
    out: dict[str, str] = {}
    try:
        with open(_secrets_path(pid), encoding="utf-8") as f:
            for line in f:
                m = re.match(r'\s*export\s+(\w+)=(.*)', line.rstrip("\n"))
                if not m:
                    continue
                try:
                    parts = shlex.split(m.group(2))   # 解开 shell 引号，原样还原值
                    out[m.group(1)] = parts[0] if parts else ""
                except ValueError:
                    out[m.group(1)] = m.group(2)
    except OSError:
        pass
    return out


def _save_deploy_creds(pid: str, creds: dict) -> int:
    """覆盖式保存部署凭证到 ~/.productflow/secrets/<id>.env（目录 700 / 文件 600）。
    只接受合法 KEY（字母/下划线开头）；值用 shlex.quote 做 shell 安全转义（不再静默删引号，
    含 " ' $ ` \\ 等特殊字符的 token/密码都原样保留，且文件仍可被 shell source）。返回写入条数。"""
    os.makedirs(SECRETS_DIR, exist_ok=True)
    try:
        os.chmod(SECRETS_DIR, 0o700)
    except OSError:
        pass
    clean = {}
    for k, v in (creds or {}).items():
        if not CRED_KEY_RE.match(str(k)):
            continue
        clean[str(k)] = str(v).replace("\n", " ").strip()   # 仅去掉换行（保持一行一条），其余原样保留
    path = _secrets_path(pid)
    body = "".join(f"export {k}={shlex.quote(v)}\n" for k, v in clean.items())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return len(clean)


def _inject_deploy_creds(env: dict, pid: str) -> None:
    """把某项目的部署凭证注入 env——⑦部署 Agent spawn 时调用，agent 直接用 $PF_SSH_HOST 等。"""
    for k, v in _load_deploy_creds(pid).items():
        env[k] = v


def _mask_secret(v: str) -> str:
    """脱敏展示：只露末 4 位，其余打码——网页只回显「存了哪些键、大概是什么」，不回吐明文。"""
    v = str(v)
    if len(v) <= 4:
        return "••••"
    return "••••" + v[-4:]


def _auto_research(pf: str, instruction: str = "") -> None:
    """后台 spawn claude 当完整 agent，按 phase-1-research.md 跑市场调研全流程：
    竞品搜索→截图→风格/卖点分析→核心矛盾分析→复刻要点，逐步登记产物并更新 step 状态。
    instruction：用户对本次（重）做的额外要求，注入 prompt——避免重做还是无脑跑一样的东西。"""
    project_root = os.path.dirname(pf)
    ps = os.path.join(SKILL_DIR, "scripts", "pf_state.py")
    appstore = os.path.join(SKILL_DIR, "scripts", "appstore_shots.py")
    doc = os.path.join(SKILL_DIR, "references", "phase-1-research.md")
    prompt = (
        "你是 ProductFlow 市场调研 Agent（阶段①），headless 运行，必须用工具实际完成任务（不要只输出描述）。\n"
        f"完整做法见手册：{doc}——先读它，再执行阶段①全部步骤。\n"
        f"项目目录：{project_root}（产品定位/需求见 .productflow/brief.json 与 wizard.json，先读了解要做什么产品）。\n"
        "重要：每个 Bash 调用都是独立 shell，登记命令必须每次写完整 `python3 <绝对路径> --dir <绝对路径> ...`，禁止用 $PF 等 shell 变量缩写（否则登记全部失效）。\n"
        "按下面步骤做，完成一步就登记一步（不要攒到最后，前端实时显示进度）：\n"
        "1. WebSearch 找 3-6 个同品类竞品的落地页 URL。\n"
        "2. 用 playwright 对每个竞品落地页整页截图，存 artifacts/phase-1/screenshots/<域名>.png（先 mkdir -p）。\n"
        "2b. 【仅当主平台=APP】先读 .productflow/wizard.json 的 primary；若是 APP，再补抓商店官方特色截图（真实 App 界面，比官网直观）：\n"
        f"    python3 {appstore} --platform both --term \"<品类英文词>\" --out artifacts/phase-1/appstore --limit 3 --max-shots 6\n"
        f"    然后按生成的 manifest.json 逐张登记：python3 {ps} --dir {project_root} artifact 1 artifacts/phase-1/appstore/<子目录>/<n>.png --title \"<App名> 商店截图\"\n"
        "    （iOS 稳；Android best-effort，抓不到就跳过、别卡住。非 APP 项目跳过本步。）\n"
        "3. 逐个分析竞品风格/卖点，写 artifacts/phase-1/analysis/<域名>.md。\n"
        "4. 做核心矛盾分析，写 artifacts/phase-1/core-analysis.mm.md（markmap 导图源）。\n"
        "5. 汇总 artifacts/phase-1/competitors.md（竞品矩阵）+ artifacts/phase-1/replicate-notes.md（复刻要点，供后续设计阶段用）。\n"
        f"每产出一个文件就登记：python3 {ps} --dir {project_root} artifact 1 artifacts/phase-1/<文件> --title \"<标题>\"\n"
        f"每完成一步就更新：python3 {ps} --dir {project_root} step 1 <step-id> --status done"
        "（step-id: search-competitors / capture-screenshots / analyze-style / core-analysis / replicate-report）\n"
        f"全部做完：python3 {ps} --dir {project_root} phase 1 --status done\n"
        "复刻红线：只学竞品布局/信息架构/风格思路，不抄文案、不盗图。只做这件事，完成即停。"
    )
    if instruction:
        prompt += f"\n\n★用户对这次市场调研的额外要求（务必优先遵循，不要无视）：{instruction}"
    _log_reset(pf, "research", "开始市场调研")
    _run_claude_streaming(pf, "research", prompt, project_root, timeout=1200)
    print("[research] 结束", file=sys.stderr)


# 面板阶段（④页面设计交给画布，这里给 ⑤⑥⑦）的「让 Agent 做本阶段」配置
_STAGE_DOC = {4: "phase-4-pages.md", 5: "phase-5-spec.md",
              6: "phase-6-implement.md", 7: "phase-7-deploy.md"}
_STAGE_NAME = {4: "页面设计", 5: "功能与数据设计", 6: "开发实现", 7: "部署上线"}
_STAGE_STEPS = {
    4: "page-map / design-pages / platform-versions / finalize-direction",
    5: "module-list / er-diagram / schema-ddl / api-contract / pick-template",
    6: "scaffold / frontend / backend / testing / api-docs",
    7: "pick-target / deploy / smoke-test / handoff-report",
}
# 各阶段典型的「该让用户拍板」决策点——提示 Agent 用 choice ask 抛到网页
_STAGE_DECISION = {
    5: "选开发模板（pick-template）时，用 choice ask 抛 T1/T2/T3 让用户点选后再继续。",
    7: "选部署目标（pick-target）时用 choice ask 抛 本机/Cloudflare/服务器 + Docker/systemd 让用户点选。"
       "部署凭证（SSH 地址/用户/端口/token 等）由用户在⑦的「凭证」表单填好、已作为环境变量注入你的运行环境，"
       "直接用即可（缺什么再用 choice ask 或 CLI 让用户补，别瞎猜）。",
}


def _auto_stage(pf: str, phase: int, instruction: str = "", pid: str | None = None) -> None:
    """后台 spawn claude 当完整 agent，按 phase-N-*.md 跑某个面板阶段（⑤⑥⑦，及④兜底）全流程。
    遇歧义点提示用 choice ask 抛给用户点选；instruction = 用户对本次（重）做的额外要求。
    phase 7（部署）会把用户填的部署凭证作为环境变量注入 agent 的运行环境。"""
    project_root = os.path.dirname(pf)
    ps = os.path.join(SKILL_DIR, "scripts", "pf_state.py")
    name = _STAGE_NAME.get(phase, f"阶段{phase}")
    doc = os.path.join(SKILL_DIR, "references", _STAGE_DOC.get(phase, ""))
    steps = _STAGE_STEPS.get(phase, "")
    decision = _STAGE_DECISION.get(phase, "")
    prompt = (
        f"你是 ProductFlow「{name}」Agent（阶段{phase}），headless 运行，必须用工具实际完成任务（不要只输出描述）。\n"
        f"完整做法见手册：{doc}——先读它，再执行本阶段全部步骤。\n"
        f"项目目录：{project_root}（先读 .productflow/state.json、brief.json 了解产品与诉求；前序阶段产物在 artifacts/phase-*/，请基于它们做）。\n"
        "重要：每个 Bash 调用都是独立 shell，命令必须每次写完整 `python3 <绝对路径> --dir <绝对路径> ...`，禁止用 $PF 等 shell 变量缩写（否则登记全部失效）。\n"
        f"逐步做、完成一步就登记一步（不要攒到最后，前端在实时显示进度）。本阶段 step-id 依次为：{steps}。\n"
        f"每完成一步：python3 {ps} --dir {project_root} step {phase} <step-id> --status done\n"
        f"每产出一个文件：python3 {ps} --dir {project_root} artifact {phase} artifacts/phase-{phase}/<文件> --title \"<标题>\"（产品代码本身放项目根目录，不放 .productflow/）。\n"
        f"遇到该让用户拍板的歧义点：用 python3 {ps} --dir {project_root} choice ask --stage {phase} --question '...' --option A --option B "
        "把选项抛到网页让用户点选（命令会输出一个 ch-xxxx 的 id）；"
        f"**接着必须** python3 {ps} --dir {project_root} choice wait <那个id> --timeout 600 阻塞等用户点选，读到 answer 再继续——"
        "拿到 answer 之前不要写相关产物、不要标 phase done；若超时（answer 仍为空）就按手册决策树自己选一个并 reply 说明。"
        + (f"{decision}\n" if decision else "\n")
        + f"全部做完：python3 {ps} --dir {project_root} phase {phase} --status done\n"
        "只做本阶段，完成即停。"
    )
    if phase in (6, 7):
        # ⑥截图/E2E、⑦线上冒烟截图都要浏览器；headless 无任何浏览器 MCP，别让 agent 乱找
        prompt += ("\n\n⚠️ 浏览器：你 headless 后台运行，**没有任何浏览器 MCP**（playwright MCP / claude-in-chrome 都不可用）——"
                   "不要 ToolSearch 找浏览器 MCP、不要试 claude-in-chrome。需要截图/E2E 就直接用本机已装的 "
                   "Python Playwright（`from playwright.sync_api import sync_playwright`，chromium headless，桌面 1440 / 移动 390 整页截图），"
                   "或 webapp-testing / playwright-cli skill；E2E 落成项目内可复跑的 @playwright/test 文件。")
    env = dict(os.environ)
    if phase == 7:
        # 部署阶段：把用户在网页凭证表单填的值注入 env，agent 直接 $PF_SSH_HOST 等使用
        creds = _load_deploy_creds(pid) if pid else {}
        if creds:
            _inject_deploy_creds(env, pid)
            prompt += ("\n\n部署凭证已作为环境变量注入（用户在⑦凭证表单填的），命令里直接引用即可："
                       + "、".join("$" + k for k in creds)
                       + "。例如 ssh -p \"$PF_SSH_PORT\" \"$PF_SSH_USER@$PF_SSH_HOST\"。"
                       "安全：不要把这些值打印进 agent-log / 产物 / 留言里。")
        else:
            prompt += ("\n\n（用户还没填部署凭证。需要 SSH 地址/账号等就用 choice ask 或在 CLI 让用户补，"
                       "别把占位值瞎填进命令。）")
    if instruction:
        prompt += f"\n\n★用户对本阶段的额外要求（务必优先遵循，不要无视）：{instruction}"
    _log_reset(pf, f"stage-{phase}", f"开始{name}")
    try:
        _run_claude_streaming(pf, f"stage-{phase}", prompt, project_root, env=env, timeout=1800)
    finally:
        with _STAGE_RUN_LOCK:
            _STAGE_RUNNING.discard((pid, phase))   # 跑完/异常都释放，允许下次重做
    print(f"[stage-{phase}] 结束", file=sys.stderr)


def _auto_page_version(pf: str, page_id: str, platform: str) -> None:
    """后台 spawn claude 为④页面设计画布里某个页面生成指定平台的设计稿，并挂版本。
    沿用③定的视觉基调，按平台尺寸/交互习惯出图，存 artifacts/phase-4/ 并 page set --add-version。"""
    project_root = os.path.dirname(pf)
    ps = os.path.join(SKILL_DIR, "scripts", "pf_state.py")
    doc = os.path.join(SKILL_DIR, "references", "phase-4-pages.md")
    img_skill = os.path.expanduser("~/.claude/skills/openai-image-gen")
    plat_name = {"PC": "PC 端（桌面 web）", "H5": "移动 web（H5）", "APP": "APP 端"}.get(platform, platform)
    out_dir = os.path.join(pf, "artifacts", "phase-4")
    prompt = (
        "你是 ProductFlow 页面设计 Agent（阶段④），headless 运行，必须用工具实际完成任务（不要只输出描述）。\n"
        f"任务：为某个页面设计 {plat_name} 版的设计稿（只做这一页、这一个平台）。\n"
        f"做法见手册：{doc}。\n"
        f"项目目录：{project_root}。先读状态拿到该页面与③定的视觉基调：python3 {ps} --dir {project_root} status\n"
        f"再读 explore（selectedHero=③定的首图基调、styleSummary=风格）：python3 {ps} --dir {project_root} explore show\n"
        f"目标页面 id：{page_id}，目标平台：{platform}。\n"
        "重要：每个 Bash 调用都是独立 shell，命令必须每次写完整 `python3 <绝对路径> --dir <绝对路径> ...`，禁止用 $PF 等 shell 变量缩写。\n"
        f"务必沿用 ③ 选定首图的视觉基调（配色/字体气质/质感）保持整套设计一致；按 {platform} 的尺寸与交互习惯排版。\n"
        f"步骤：\n1. 先标记设计中：python3 {ps} --dir {project_root} page set {page_id} --status designing\n"
        f"2. 用 openai-image-gen（脚本 {img_skill}/scripts/gen.py）按基调+该页内容生成设计稿，显式输出到 {out_dir}（先 mkdir -p）：\n"
        f"   python3 {img_skill}/scripts/gen.py ... --out-dir {out_dir}\n"
        f"3. ls {out_dir} 确认真实文件名后，挂版本：\n"
        f"   python3 {ps} --dir {project_root} page set {page_id} --add-version artifacts/phase-4/<实际文件名> --platform {platform}\n"
        f"4. 登记产物：python3 {ps} --dir {project_root} artifact 4 artifacts/phase-4/<实际文件名> --title \"<页面名> {platform} 版\"\n"
        "只做这一页这一个平台的版本，完成即停。版权红线：原创设计，不盗用竞品图。"
    )
    env = dict(os.environ)
    env["PF_PROJECT"] = project_root
    _inject_openai_env(env)
    _log_reset(pf, "stage-4", f"生成页面 {page_id} 的 {platform} 版")
    _run_claude_streaming(pf, "stage-4", prompt, project_root, env=env, timeout=900)
    print(f"[page-version] {page_id}/{platform} 结束", file=sys.stderr)


def _auto_explore(pf: str, req: dict) -> None:
    """后台 spawn claude -p 当完整 agent，按手册跑 search-refs / gen-heroes，结果写进 explore.json。
    claude 不在/超时/未完成则 request 残留，inbox 里的 explore-request 仍在，可由真人 agent 接单降级。"""
    if not isinstance(req, dict):
        return
    kind = req.get("kind")
    project_root = os.path.dirname(pf)
    pf_state = os.path.join(SKILL_DIR, "scripts", "pf_state.py")
    if kind == "search-refs":
        design_doc = os.path.join(SKILL_DIR, "references", "phase-2-refs.md")
        refs_dir = os.path.join(pf, "artifacts", "phase-2", "refs")
        keywords = req.get("keywords")
        seed = req.get("seedRef") if isinstance(req.get("seedRef"), dict) else None
        # 零输入：用户没给关键词 → 让 agent 读 brief 自己推断
        kw_line = (f"风格关键词：{keywords}\n" if keywords else
                   "用户没给风格关键词（零输入）——先读 .productflow/brief.json 理解产品定位/目标用户/核心需求，"
                   "自己推断 2-3 个贴切的风格/品类关键词再搜，别空手搜。\n")
        # 找更多类似这张：以用户选中的一张图为种子，结合需求做下一轮精炼搜索
        seed_line = ""
        if seed and seed.get("file"):
            seed_line = (f"【找更多类似这张·精炼轮】种子参考图：{seed.get('file')}"
                         f"（标题：{seed.get('title', '')}，源：{seed.get('source', '')}）。\n"
                         "先用 Read 打开这张种子图，看清它的视觉风格（配色/版式/字体气质/质感/品类），"
                         "再据此 + 产品定位去搜「更多同一风格」的参考，不要再找跑偏的方向。\n")
        prompt = (
            "你是 ProductFlow 找参考 Agent（阶段②），headless 运行，必须用工具实际完成任务（不要只输出描述）。\n"
            "任务：去 Dribbble 找落地页/UI 设计参考，**下载高清原图**（不是缩略图截图，要让用户能放大看细节）。\n"
            f"做法见手册：{design_doc} 的「找参考协作」节。\n"
            + kw_line + seed_line +
            f"产品：{req.get('product')}\n"
            "📱 **必须区分设备**：先读 `.productflow/wizard.json` 看 `platforms` 与主平台 `primary`——"
            "PC=桌面 web 落地页、H5=移动 web、APP=App UI。按**主平台**调整搜索词和筛选，"
            "桌面端就搜「landing page / web design」这类、移动端就搜「mobile app UI / mobile landing / app screen」这类，"
            "**别给移动端产品找一堆桌面 web 落地页，反之亦然**。多平台项目优先按 primary，必要时各平台都找几张并在 title 里标注「(PC)/(移动)」。\n"
            "⚠️ 浏览器工具（重要，别浪费步骤）：你在 headless 后台运行，**没有任何浏览器 MCP**——"
            "playwright MCP、claude-in-chrome 都不可用。**不要**去 ToolSearch 找 playwright MCP、不要试 claude-in-chrome MCP。"
            "本机已装 **Python Playwright（chromium headless）**：直接 `from playwright.sync_api import sync_playwright` 写个小脚本抓取，"
            "这是验证过最快可行的路径（需要交互式浏览也可用 `playwright-cli` skill，但批量下图直接写脚本最省事）。\n"
            "重要执行约束：每个 Bash 工具调用都是独立 shell，登记命令必须每次写完整 `python3 <绝对路径> --dir <绝对路径> ...`，"
            "禁止用 $PF 之类 shell 变量缩写（否则登记全部失效）。\n"
            "步骤（用 Python Playwright 脚本完成 1-2）：\n"
            "1. 打开 https://dribbble.com/search/<关键词>（URL 编码、空格转 -），等加载，收集结果里每个作品的**详情页链接**（/shots/...）。\n"
            "2. 取前 6-9 个详情页：逐个打开，读详情页主图 <img> 的真实 src（一般是 cdn.dribbble.com 的高清原图 URL），"
            f"用 urllib/requests 下载这张**高清原图**到 {refs_dir}/<n>.png（先 mkdir -p）。\n"
            "   ⚠️ **不要用截图兜底**：某张取不到真实高清图 URL 就直接跳过它（宁可少几张，也不存模糊截图/空白图）；"
            "如果整体访问失败（打不开 Dribbble、一张真图都没拿到），**不要 done-request**、不要登记任何东西，直接结束并在最后一句明确说「访问失败」——前端会提示用户重试。\n"
            "3. 关键：每下载一张就立刻登记一次，不要攒到最后（前端实时显示进度）。source 填该作品**详情页 URL**（用户可点开看原帖）：\n"
            f"   python3 {pf_state} --dir {project_root} explore add-ref artifacts/phase-2/refs/<n>.png --title \"<一句话风格描述>\" --source \"<该作品详情页 URL>\"\n"
            f"4. 全部登记完执行：python3 {pf_state} --dir {project_root} explore done-request --kind search-refs\n"
            "只做这件事，完成即停。参考仅供风格判断，不抄袭、不进最终产品。"
        )
        timeout = 600
    elif kind == "gen-heroes":
        design_doc = os.path.join(SKILL_DIR, "references", "phase-3-hero.md")
        heroes_dir = os.path.join(pf, "artifacts", "phase-3", "heroes")
        img_skill = os.path.expanduser("~/.claude/skills/openai-image-gen")
        prompt = (
            "你是 ProductFlow 首图设计 Agent（阶段③），headless 运行，必须用工具实际完成任务（不要只输出描述）。\n"
            "任务：按用户选中的参考，生成落地页首图（hero）。\n"
            f"做法见手册：{design_doc} 的「首图生成协作」节。\n"
            "重要执行约束：每个 Bash 工具调用都是独立 shell，定义的 shell 变量不会跨调用保留。"
            "所有命令（gen.py、pf_state、add-hero、done-request）每次都必须写完整的绝对路径，"
            "禁止用 $PF / $GEN 之类 shell 变量缩写命令——上一轮就因为用了 `$PF=...` 然后 `$PF add-hero`，"
            "变量在下个 Bash 调用里为空，导致 3 张新图全部没 add-hero 成功、explore.json 仍指向旧图。\n"
            f"先读状态：python3 {pf_state} --dir {project_root} explore show\n"
            f"其中 selectedRefs 为用户选中的参考（图在 {pf}/<其 file>）。\n"
            "**若 selectedRefs 为空**：用户没特意挑参考——有 refs 就综合所有 refs 的共同风格；"
            "refs 也没有就直接按 .productflow/brief.json 的产品定位/目标用户自定一个贴切风格。"
            "总之别因为没选参考就停下不做（零输入也要能出首图）。\n"
            "步骤（严格按顺序）：\n"
            "1. 查看选中参考（空则按上一行兜底），总结共同视觉风格（配色/字体气质/布局/质感），写入：\n"
            f"   python3 {pf_state} --dir {project_root} explore set-summary \"<风格一句话>\"\n"
            f"2. 用 openai-image-gen skill（脚本在 {img_skill}/scripts/gen.py）按该风格+产品主题生成 2-4 版落地页首图。\n"
            f"   必须显式把图直接生到 heroes 目录、并开并发（先 mkdir -p {heroes_dir}）：\n"
            f"   python3 {img_skill}/scripts/gen.py ... --out-dir {heroes_dir} --concurrency 4\n"
            f"   （--out-dir 用上面这个绝对路径，不要用默认的 ~/Projects/tmp，也不要用 shell 变量传目录。gen.py 输出文件名形如 01-<风格>.png，不是 1.png。）\n"
            f"3. 生图全部完成后，先列出真实文件名：ls {heroes_dir}\n"
            "4. 对 ls 出来的「每一个」实际文件，逐个执行完整命令登记（每条都写全，禁止 shell 变量；不要攒到最后，前端实时显示进度）：\n"
            f"   python3 {pf_state} --dir {project_root} explore add-hero artifacts/phase-3/heroes/<实际文件名> --style \"<风格标签>\"\n"
            "5. 确认每张都 add-hero 成功后（必要时再跑一次 explore show 核对 heroes 已指向新文件），最后才执行：\n"
            f"   python3 {pf_state} --dir {project_root} explore done-request --kind gen-heroes\n"
            "只做这件事，完成即停。"
        )
        timeout = 900
    elif kind == "collect-ref":
        # 用户贴的参考链接：打开截图、登记为一张参考
        design_doc = os.path.join(SKILL_DIR, "references", "phase-2-refs.md")
        refs_dir = os.path.join(pf, "artifacts", "phase-2", "refs")
        url = str(req.get("url") or "").strip()
        prompt = (
            "你是 ProductFlow 找参考 Agent（阶段②），headless 运行，必须用工具实际完成任务（不要只输出描述）。\n"
            f"任务：采集用户提供的这个参考链接：{url}\n"
            f"做法可参考手册：{design_doc} 的「找参考协作」节。\n"
            "⚠️ 浏览器工具：你在 headless 后台运行，**没有浏览器 MCP**（playwright MCP / claude-in-chrome 都没有）——"
            "不要去 ToolSearch 找 MCP，直接用本机已装的 **Python Playwright（chromium headless）** 写脚本截图（或 `playwright-cli` skill）。\n"
            "重要：每个 Bash 调用是独立 shell，登记命令必须写完整 `python3 <绝对路径> --dir <绝对路径> ...`，禁止用 $PF 缩写。\n"
            "步骤：\n"
            f"1. 用 Python Playwright 打开 {url}，等页面加载，整页截图存 {refs_dir}/<简短英文名>.png（先 mkdir -p）。"
            "若该链接本身就是一张图片，直接下载即可。"
            "**若链接访问失败/打不开，不要存空白图、不要 done-request，直接结束并明确说「访问失败」让用户重试。**\n"
            f"2. 登记：python3 {pf_state} --dir {project_root} explore add-ref artifacts/phase-2/refs/<文件名> --title \"<一句话风格描述>\" --source \"{url}\"\n"
            f"3. 完成：python3 {pf_state} --dir {project_root} explore done-request --kind collect-ref\n"
            "只采集这一个链接，完成即停。版权红线：只供风格判断，不抄文案、不盗图。"
        )
        timeout = 300
    else:
        return
    env = dict(os.environ)
    env["PF_PROJECT"] = project_root
    _inject_openai_env(env)
    phase = kind  # "search-refs" | "gen-heroes" | "collect-ref"
    _log_reset(pf, phase, "开始" + {"search-refs": "找参考截图", "gen-heroes": "生成首图",
                                    "collect-ref": "采集参考链接"}.get(kind, ""))
    _run_claude_streaming(pf, phase, prompt, project_root, env=env, timeout=timeout)
    # 进程已退出：若 request 槽还在（agent 没 done-request，多半 claude 挂了/未登录/超时/没跑完），
    # 自动清掉卡住的槽，让前端「生成中」复位、按钮恢复可重试（error 行已在 agent-log 里可见）。
    try:
        exp = os.path.join(pf, "explore.json")
        exj = _read_json(exp)
        if isinstance(exj.get("request"), dict) and kind in exj["request"]:
            del exj["request"][kind]
            _atomic_write_json(exp, exj)
            _log_line(pf, phase, "error", "❌ 未完成请求，已自动清除（可重试）")
    except Exception:  # noqa: BLE001  清理失败不该让线程崩
        pass
    print(f"[explore] {kind} 结束 → {pf}/explore.json", file=sys.stderr)


_CANVAS_LOCK = threading.Lock()  # canvas.json read-modify-write 串行化（两块画布并发 save）
_STAGE_RUN_LOCK = threading.Lock()        # 保护 _STAGE_RUNNING
_STAGE_RUNNING: set = set()               # {(pid, phase)} 正在跑的阶段——防双开同阶段 agent


def _read_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _registry_entries() -> list[dict]:
    """All valid registry entries, sorted by id. Broken files are skipped."""
    out = []
    try:
        names = sorted(os.listdir(PROJECTS_DIR))
    except FileNotFoundError:
        return out
    for fn in names:
        if not fn.endswith(".json"):
            continue
        pid = fn[:-5]
        if not ID_RE.match(pid):
            continue
        try:
            reg = _read_json(os.path.join(PROJECTS_DIR, fn))
        except Exception:
            continue
        reg["id"] = pid
        out.append(reg)
    return out


def _resolve(pid: str) -> str | None:
    """Registry id -> absolute project path, or None."""
    if not ID_RE.match(pid):
        return None
    try:
        reg = _read_json(os.path.join(PROJECTS_DIR, pid + ".json"))
        path = reg.get("path")
        return path if isinstance(path, str) and path else None
    except Exception:
        return None


def _dir_label(path: str) -> str:
    parts = [s for s in str(path).replace("\\", "/").split("/") if s]
    return "/".join(parts[-2:])


def _project_summary(reg: dict) -> dict:
    pid = reg["id"]
    path = reg.get("path") or ""
    pf = os.path.join(path, ".productflow")
    item = {
        "id": pid, "name": pid, "dir_label": _dir_label(path),
        "phases": [], "done": 0, "current_phase": None, "updated": None,
        "cover": None, "working": False, "missing": False, "error": False,
        "archived": bool(reg.get("archived")), "health": None,
    }
    try:
        item["health"] = _read_json(os.path.join(pf, "health.json"))
    except Exception:
        pass
    state_path = os.path.join(pf, "state.json")
    if not os.path.isdir(path) or not os.path.exists(state_path):
        item["missing"] = True
        return item
    try:
        state = _read_json(state_path)
    except Exception:
        item["error"] = True
        return item
    item["name"] = state.get("product") or pid
    phases = state.get("phases") or []
    item["phases"] = [{"id": ph.get("id"), "status": ph.get("status")} for ph in phases]
    item["done"] = sum(1 for ph in phases if ph.get("status") == "done")
    item["current_phase"] = state.get("current_phase")
    item["updated"] = state.get("updated")
    try:
        ts = _dt.datetime.strptime(item["updated"], "%Y-%m-%d %H:%M:%S")
        item["working"] = (_dt.datetime.now() - ts).total_seconds() < 120
    except Exception:
        pass
    latest = None
    for ph in phases:
        for a in ph.get("artifacts") or []:
            if a.get("type") == "image" and a.get("file"):
                if latest is None or str(a.get("ts") or "") > str(latest.get("ts") or ""):
                    latest = a
    if latest:
        rel = latest["file"]
        if rel.startswith("artifacts/"):
            rel = rel[len("artifacts/"):]
        item["cover"] = f"/p/{pid}/artifacts/{rel}"
    return item


def _projects_payload() -> dict:
    projects = []
    for reg in _registry_entries():
        try:
            projects.append(_project_summary(reg))
        except Exception:
            projects.append({
                "id": reg["id"], "name": reg["id"], "dir_label": _dir_label(reg.get("path") or ""),
                "phases": [], "done": 0, "current_phase": None, "updated": None,
                "cover": None, "working": False, "missing": False, "error": True,
                "archived": bool(reg.get("archived")), "health": None,
            })
    pending = []
    try:
        names = sorted(os.listdir(PENDING_DIR))
    except FileNotFoundError:
        names = []
    for fn in names:
        if not fn.endswith(".json"):
            continue
        try:
            d = _read_json(os.path.join(PENDING_DIR, fn))
            pending.append({"file": fn, "name": d.get("name"), "brief": d.get("brief"),
                            "created": d.get("created")})
        except Exception:
            continue
    return {"version": VERSION, "projects": projects, "pending": pending}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        if host in ALLOWED_HOSTS:
            return True
        self._send(403, b"forbidden", "text/plain")
        return False

    def _post_origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if origin and urllib.parse.urlsplit(origin).hostname not in ALLOWED_HOSTS:
            self._send(403, b"forbidden", "text/plain")
            return False
        sfs = self.headers.get("Sec-Fetch-Site")
        if sfs and sfs not in ("same-origin", "none"):
            self._send(403, b"forbidden", "text/plain")
            return False
        return True

    def _console(self) -> None:
        try:
            with open(CONSOLE_HTML, "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        except FileNotFoundError:
            self._send(500, b"console.html missing", "text/plain")

    def do_GET(self):
        if not self._host_ok():
            return
        path = self.path.split("?")[0]
        qs = urllib.parse.parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        if path == "/":
            self._console()
        elif path == "/api/version":
            self._json({"app": "productflow", "version": VERSION})
        elif path == "/api/update-check":
            # 操作台用：当前版本 vs GitHub 远端版本。?refresh=1 重新拉一次
            latest = _refresh_latest() if qs.get("refresh") else _latest_version
            avail = bool(latest) and _version_tuple(latest) > _version_tuple(VERSION)
            self._json({"current": VERSION, "latest": latest, "update_available": avail,
                        "repo": UPDATE_REPO, "git": bool(_repo_root())})
        elif path == "/api/projects":
            self._json(_projects_payload())
        elif path.startswith("/vendor/"):
            name = os.path.basename(path)
            ctype = {
                "d3.min.js": "application/javascript; charset=utf-8",
                "markmap-lib.js": "application/javascript; charset=utf-8",
                "markmap-view.js": "application/javascript; charset=utf-8",
                "viewer.min.js": "application/javascript; charset=utf-8",
                "viewer.min.css": "text/css; charset=utf-8",
            }.get(name)
            if ctype is None:
                self._send(404, b"not found", "text/plain")
                return
            try:
                with open(os.path.join(SKILL_DIR, "assets", "vendor", name), "rb") as f:
                    self._send(200, f.read(), ctype)
            except FileNotFoundError:
                self._send(404, b"not found", "text/plain")
        else:
            m = P_ROUTE.match(path)
            if not m:
                self._send(404, b"not found", "text/plain")
                return
            pid, sub = m.group(1), m.group(2) or ""
            if sub in ("", "/"):
                self._console()
                return
            root = _resolve(pid)
            if root is None:
                self._send(404, b"not found", "text/plain")
                return
            pf = os.path.join(root, ".productflow")
            if sub == "/api/state":
                try:
                    with open(os.path.join(pf, "state.json"), encoding="utf-8") as f:
                        self._send(200, f.read().encode(), "application/json; charset=utf-8")
                except FileNotFoundError:
                    self._json({"error": "not_initialized"}, 404)
            elif sub == "/api/inbox":
                msgs = []
                try:
                    with open(os.path.join(pf, "inbox.jsonl"), encoding="utf-8") as f:
                        msgs = [json.loads(line) for line in f if line.strip()]
                except FileNotFoundError:
                    pass
                self._json({"messages": msgs})
            elif sub == "/api/agent-log":
                # ?phase=brief|search-refs|gen-heroes 取该阶段的进度流
                phase = (qs.get("phase", ["brief"])[0] or "brief").strip()
                lines = []
                try:
                    with open(_agent_log_path(pf, phase), encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    lines.append(json.loads(line))
                                except json.JSONDecodeError:
                                    continue
                except FileNotFoundError:
                    pass
                self._json({"lines": lines[-50:]})
            elif sub == "/api/canvas":
                # 每阶段一块画布：canvas.json = {"3": {view,items,notes}, "4": {...}}
                # GET ?stage=N 返回该阶段；缺省/缺失 → 空结构
                stage = (qs.get("stage", [""])[0] or "").strip()
                try:
                    with open(os.path.join(pf, "canvas.json"), encoding="utf-8") as f:
                        data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    data = {}
                if not isinstance(data, dict):
                    data = {}
                cell = data.get(stage) if stage else None
                if not isinstance(cell, dict):
                    cell = {"view": None, "items": {}, "notes": []}
                self._json(cell)
            elif sub == "/api/health":
                try:
                    with open(os.path.join(pf, "health.json"), encoding="utf-8") as f:
                        self._send(200, f.read().encode(), "application/json; charset=utf-8")
                except FileNotFoundError:
                    self._json({})
            elif sub == "/api/pages":
                try:
                    with open(os.path.join(pf, "pages.json"), encoding="utf-8") as f:
                        self._send(200, f.read().encode(), "application/json; charset=utf-8")
                except FileNotFoundError:
                    self._json({"pages": []})
            elif sub == "/api/choices":
                try:
                    with open(os.path.join(pf, "choices.json"), encoding="utf-8") as f:
                        self._send(200, f.read().encode(), "application/json; charset=utf-8")
                except FileNotFoundError:
                    self._json({"choices": []})
            elif sub == "/api/deploy-creds":
                # 只回显「存了哪些键 + 脱敏值」，绝不回吐明文凭证给网页
                creds = _load_deploy_creds(pid)
                self._json({"keys": [{"key": k, "masked": _mask_secret(v)} for k, v in creds.items()]})
            elif sub == "/api/explore":
                try:
                    with open(os.path.join(pf, "explore.json"), encoding="utf-8") as f:
                        self._send(200, f.read().encode(), "application/json; charset=utf-8")
                except FileNotFoundError:
                    self._json({"stylePrefs": [], "request": {}, "refs": [], "selectedRefs": [],
                                "styleSummary": "", "heroes": [], "selectedHero": ""})
            elif sub == "/api/brief":
                try:
                    with open(os.path.join(pf, "brief.json"), encoding="utf-8") as f:
                        self._send(200, f.read().encode(), "application/json; charset=utf-8")
                except FileNotFoundError:
                    self._json({"description": "", "request": None, "questions": [], "confirmed": False,
                                "summary": {"goal": "", "users": "", "need": "", "scope": ""}, "ready": False})
            elif sub == "/api/wizard":
                try:
                    with open(os.path.join(pf, "wizard.json"), encoding="utf-8") as f:
                        self._send(200, f.read().encode(), "application/json; charset=utf-8")
                except FileNotFoundError:
                    self._json({"brief": "", "platforms": [], "primary": None,
                                "priority": [], "stylePrefs": []})
            elif sub.startswith("/artifacts/"):
                rel = os.path.normpath(sub[len("/artifacts/"):].lstrip("/"))
                base = os.path.realpath(os.path.join(pf, "artifacts"))
                full = os.path.realpath(os.path.join(base, rel))
                if not full.startswith(base + os.sep) and full != base:
                    self._send(403, b"forbidden", "text/plain")
                    return
                try:
                    ext = os.path.splitext(full)[1].lower()
                    ctype = {
                        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                        ".webp": "image/webp", ".svg": "image/svg+xml",
                        ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
                    }.get(ext, "text/plain; charset=utf-8")
                    with open(full, "rb") as f:
                        self._send(200, f.read(), ctype)
                except (FileNotFoundError, IsADirectoryError):
                    self._send(404, b"not found", "text/plain")
            else:
                self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if not self._host_ok():
            return
        if not self._post_origin_ok():
            return
        path = self.path.split("?")[0]
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError
        except Exception:
            self._json({"error": "bad_json"}, 400)
            return

        if path == "/api/update":
            # 自动更新：git pull 拉新版 + 跑数据迁移钩子。数据（~/.productflow + 各项目目录）在 skill 外，自动保留。
            root = _repo_root()
            if not root:
                self._json({"ok": False, "error": "not_git_checkout",
                            "hint": "本地不是 git 克隆装的，自动更新只支持 git clone 安装；或手动重装最新包"}, 400)
                return
            pull = subprocess.run(["git", "-C", root, "pull", "--ff-only"],
                                  capture_output=True, text=True, timeout=90)
            if pull.returncode != 0:
                self._json({"ok": False, "error": "git_pull_failed", "detail": (pull.stderr or "")[-500:]}, 500)
                return
            migrate_out = ""
            mig = os.path.join(SKILL_DIR, "scripts", "migrate.py")
            if os.path.isfile(mig):
                m = subprocess.run(["python3", mig], capture_output=True, text=True, timeout=180)
                migrate_out = ((m.stdout or "") + (m.stderr or ""))[-600:]
            new_ver = _read_version()
            global _latest_version
            _latest_version = new_ver
            self._json({"ok": True, "version": new_ver, "restart_needed": new_ver != VERSION,
                        "git": (pull.stdout or "")[-300:], "migrate": migrate_out})
            return
        if path == "/api/create":
            # 向导直接创建真项目（视觉探索需要项目目录存参考图/首图）
            # 项目名（中文/显示用）与目录名（slug/文件系统用）分开：优先用前端传的 slug
            name = (data.get("name") or "").strip() or "未命名项目"
            slug = re.sub(r"[^a-z0-9-]+", "-", (data.get("slug") or "").strip().lower()).strip("-")
            if not slug or slug == "project":   # 没填 / 项目名纯中文 → 用项目名 slug，仍为空则给唯一后缀
                slug = pf_state._slug(name)
            if slug == "project":
                slug = "project-" + os.urandom(2).hex()
            base = os.path.expanduser("~/code")
            d = os.path.join(base, slug)
            n = 1
            while os.path.isdir(os.path.join(d, ".productflow")):
                n += 1
                d = os.path.join(base, f"{slug}-{n}")
            try:
                os.makedirs(d, exist_ok=True)
                pid = pf_state.create_project(d, name)
            except Exception as ex:
                self._json({"error": str(ex)}, 500)
                return
            # 把向导收集的配置/需求落进项目（log + explore 风格偏好种子）
            pf = os.path.join(d, ".productflow")
            extras = []
            if data.get("platforms"):
                extras.append("平台:" + "/".join(data["platforms"]))
            if data.get("primary"):
                extras.append("主平台:" + data["primary"])
            brief = (data.get("brief") or "").strip()
            if brief:
                extras.append("需求:" + brief[:80])
            if extras:
                try:
                    with open(os.path.join(pf, "wizard.json"), "w", encoding="utf-8") as f:
                        json.dump({"brief": brief, "platforms": data.get("platforms"),
                                   "primary": data.get("primary"), "priority": data.get("priority")},
                                  f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            self._json({"ok": True, "id": pid, "dir": d})
            return

        if path == "/api/project-remove":
            # 从操作台移除：仅删注册表条目，磁盘项目文件原样保留（可重新 init 找回）
            pid = (data.get("id") or "").strip()
            if not ID_RE.match(pid):
                self._json({"error": "bad_id"}, 400)
                return
            try:
                os.remove(os.path.join(PROJECTS_DIR, pid + ".json"))
            except FileNotFoundError:
                pass
            self._json({"ok": True})
            return

        if path == "/api/project-delete":
            # 彻底删除：移除注册表 + 删掉磁盘项目文件夹。多重安全校验，绝不误删 home/根/非项目目录。
            pid = (data.get("id") or "").strip()
            if not ID_RE.match(pid):
                self._json({"error": "bad_id"}, 400)
                return
            target = _resolve(pid)
            if target:
                real = os.path.realpath(target)
                home = os.path.realpath(os.path.expanduser("~"))
                if os.path.isdir(real):
                    # 安全：必须内含 .productflow（确为 ProductFlow 项目）、严格在 home 之下、不是 home 本身
                    if (os.path.isdir(os.path.join(real, ".productflow"))
                            and real.startswith(home + os.sep) and real != home):
                        try:
                            shutil.rmtree(real)
                        except OSError as ex:
                            self._json({"error": str(ex)}, 500)
                            return
                    else:
                        self._json({"error": "unsafe_path"}, 400)
                        return
                # 目录已不存在 → 跳过删文件，只清注册表
            try:
                os.remove(os.path.join(PROJECTS_DIR, pid + ".json"))
            except FileNotFoundError:
                pass
            # 一并清掉该项目的部署凭证（别留孤儿明文凭证）
            try:
                os.remove(_secrets_path(pid))
            except FileNotFoundError:
                pass
            self._json({"ok": True})
            return

        if path == "/api/pending":
            name = (data.get("name") or "").strip()
            if not name:
                self._json({"error": "empty_name"}, 400)
                return
            os.makedirs(PENDING_DIR, exist_ok=True)
            stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            fn = f"{stamp}-{os.urandom(2).hex()}.json"
            entry = {
                "name": name, "brief": (data.get("brief") or "").strip(),
                "created": _now(), "v": 1,
            }
            # 向导收集的配置（平台/主平台/优先级）一并存给 Agent 接单时读取
            if isinstance(data.get("platforms"), list):
                entry["platforms"] = data["platforms"]
            if data.get("primary"):
                entry["primary"] = data["primary"]
            if isinstance(data.get("priority"), list):
                entry["priority"] = data["priority"]
            _atomic_write_json(os.path.join(PENDING_DIR, fn), entry)
            self._json({"ok": True, "file": fn})
            return

        m = P_ROUTE.match(path)
        if not m:
            self._send(404, b"not found", "text/plain")
            return
        pid, sub = m.group(1), m.group(2) or ""
        root = _resolve(pid)
        if root is None or sub not in ("/api/inbox", "/api/canvas", "/api/pages", "/api/explore", "/api/brief", "/api/research", "/api/choice", "/api/run-stage", "/api/deploy-creds"):
            self._send(404, b"not found", "text/plain")
            return
        pf = os.path.join(root, ".productflow")
        os.makedirs(pf, exist_ok=True)
        if sub == "/api/canvas":
            # per-stage 命名空间：只更新本 stage 的格子，read-modify-write 保留其他 stage。
            # canvas 由两块画布(P3/P4)各自的 save 定时器并发 POST，必须持锁避免丢更新。
            stage = str(data.get("stage") or "").strip()
            if stage not in ("3", "4"):
                self._json({"error": "bad_stage"}, 400)
                return
            cpath = os.path.join(pf, "canvas.json")
            with _CANVAS_LOCK:
                try:
                    with open(cpath, encoding="utf-8") as f:
                        cdata = json.load(f)
                    if not isinstance(cdata, dict):
                        cdata = {}
                except (FileNotFoundError, json.JSONDecodeError):
                    cdata = {}
                cdata[stage] = {
                    "view": data.get("view"),
                    "items": data.get("items") or {},
                    "notes": data.get("notes") or [],
                }
                _atomic_write_json(cpath, cdata)
            self._json({"ok": True})
            return
        if sub == "/api/pages":
            # 前端「+添加页面 / 删除页面」——增量改 pages.json（与 pf_state page 命令同一份数据）
            pages_path = os.path.join(pf, "pages.json")
            try:
                with open(pages_path, encoding="utf-8") as f:
                    pdata = json.load(f)
                if not isinstance(pdata.get("pages"), list):
                    pdata = {"pages": []}
            except (FileNotFoundError, json.JSONDecodeError):
                pdata = {"pages": []}
            action = data.get("action")
            if action == "add":
                name = (data.get("name") or "").strip()
                if not name:
                    self._json({"error": "empty_name"}, 400)
                    return
                pdata["pages"].append({
                    "id": "pg-" + os.urandom(3).hex(), "name": name,
                    "group": (data.get("group") or "未分组").strip(),
                    "status": "placeholder", "versions": [], "note": "",
                })
            elif action == "remove":
                pid_ = data.get("id")
                pdata["pages"] = [p for p in pdata["pages"] if p.get("id") != pid_]
            elif action == "gen-version":
                # 点画布上某页的空平台徽章 → spawn Agent 生成该页该平台版本
                page_id = data.get("id")
                platform = data.get("platform")
                if platform not in ("PC", "H5", "APP") or not page_id:
                    self._json({"error": "bad_version_req"}, 400)
                    return
                pg = next((p for p in pdata["pages"] if p.get("id") == page_id), None)
                if pg is None:
                    self._json({"error": "no_such_page"}, 400)
                    return
                with open(os.path.join(pf, "inbox.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": _now(), "from": "web", "type": "page-version-request",
                                        "text": f"生成「{pg.get('name')}」的 {platform} 版设计"},
                                       ensure_ascii=False) + "\n")
                threading.Thread(target=_auto_page_version, args=(pf, page_id, platform),
                                 daemon=True).start()
                self._json({"ok": True})
                return
            else:
                self._json({"error": "bad_action"}, 400)
                return
            _atomic_write_json(pages_path, pdata)
            self._json({"ok": True})
            return
        if sub == "/api/explore":
            # 前端写「风格偏好 / 发起请求 / 选择参考 / 选择首图」；agent 用 pf_state explore 写结果
            ex_path = os.path.join(pf, "explore.json")
            try:
                with open(ex_path, encoding="utf-8") as f:
                    ex = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                ex = {}
            for k in ("stylePrefs", "selectedRefs", "selectedHero"):
                if k in data:
                    ex[k] = data[k]
            # 用户删除一张参考 / 首图（含磁盘文件，安全锚定）
            if data.get("removeRef"):
                rid = data["removeRef"]
                ref = next((r for r in ex.get("refs", []) if r.get("id") == rid), None)
                ex["refs"] = [r for r in ex.get("refs", []) if r.get("id") != rid]
                ex["selectedRefs"] = [x for x in ex.get("selectedRefs", []) if x != rid]
                if ref:
                    pf_state._rm_artifact_file(root, ref.get("file"))
            if data.get("removeHero"):
                hid = data["removeHero"]
                hero = next((h for h in ex.get("heroes", []) if h.get("id") == hid), None)
                ex["heroes"] = [h for h in ex.get("heroes", []) if h.get("id") != hid]
                if hero and ex.get("selectedHero") == hero.get("file"):
                    ex["selectedHero"] = ""
                if hero:
                    pf_state._rm_artifact_file(root, hero.get("file"))
            req = data.get("request")
            if req is not None:
                # 按 kind 分槽：{"search-refs":{...}, "gen-heroes":{...}, "collect-ref":{...}}——
                # 这样 done-request --kind X 才能精确清掉自己那槽，不同阶段请求互不覆盖
                kind = req.get("kind") if isinstance(req, dict) else str(req)
                if not isinstance(ex.get("request"), dict):
                    ex["request"] = {}
                ex["request"][kind] = req
                # 同时往 inbox 投一条提示，agent 检查点能看到这次视觉探索请求
                with open(os.path.join(pf, "inbox.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": _now(), "from": "web", "type": "explore-request",
                                        "text": f"视觉探索请求：{kind}", "request": req},
                                       ensure_ascii=False) + "\n")
                # 直接 spawn claude -p 当完整 agent 跑（playwright 截图 / openai-image-gen 生图），前端轮询拿结果
                if isinstance(req, dict) and req.get("kind") in ("search-refs", "gen-heroes", "collect-ref"):
                    threading.Thread(target=_auto_explore, args=(pf, req), daemon=True).start()
            _atomic_write_json(ex_path, ex)
            self._json({"ok": True})
            return
        if sub == "/api/brief":
            # 前端写产品描述 + 发起「生成摘要」请求；agent 用 pf_state brief set-summary 回填
            br_path = os.path.join(pf, "brief.json")
            try:
                with open(br_path, encoding="utf-8") as f:
                    br = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                br = {"description": "", "request": None,
                      "summary": {"goal": "", "users": "", "need": "", "scope": ""}, "ready": False}
            if "description" in data:
                br["description"] = data["description"]
            if isinstance(data.get("questions"), list):   # 「确认」会清空待确认问题
                br["questions"] = data["questions"]
            if "confirmed" in data:                        # 「确认」=True；「重新生成」=False
                br["confirmed"] = bool(data["confirmed"])
            req = data.get("request")
            if req is not None:
                br["request"] = req
                br["ready"] = False
                if isinstance(req, dict) and req.get("kind") == "gen-summary":
                    br["questions"] = []   # 重新生成：清掉旧的待确认问题，生成完再写新的（前端不会闪回旧问题）
                with open(os.path.join(pf, "inbox.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": _now(), "from": "web", "type": "brief-request",
                                        "text": "产品需求：请生成 AI 理解摘要", "request": req},
                                       ensure_ascii=False) + "\n")
                # 直接起后台线程调本地 claude 生成摘要，前端轮询拿结果，无需 agent 守在 inbox
                if isinstance(req, dict) and req.get("kind") == "gen-summary":
                    # 优先用 request.description（已折入本次的确认/补充），br.description 保持干净不滚雪球
                    desc = (req.get("description") or br.get("description") or "").strip()
                    if desc:
                        threading.Thread(target=_auto_gen_brief, args=(pf, desc), daemon=True).start()
            _atomic_write_json(br_path, br)
            self._json({"ok": True})
            return
        if sub == "/api/research":
            # 「让 Agent 做市场调研」：投 inbox + 后台 spawn claude 跑 phase-1 全流程
            instruction = (data.get("instruction") or "").strip()
            note = "市场调研：请做竞品调研与核心矛盾分析" + (f"（要求：{instruction}）" if instruction else "")
            with open(os.path.join(pf, "inbox.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": _now(), "from": "web", "type": "research-request",
                                    "text": note}, ensure_ascii=False) + "\n")
            threading.Thread(target=_auto_research, args=(pf, instruction), daemon=True).start()
            self._json({"ok": True})
            return
        if sub == "/api/run-stage":
            # 「让 Agent 做本阶段」：面板阶段 ⑤⑥⑦（及④兜底）的通用触发
            try:
                phase = int(data.get("phase"))
            except (TypeError, ValueError):
                self._json({"error": "bad_phase"}, 400)
                return
            if phase not in _STAGE_NAME:
                self._json({"error": "bad_phase"}, 400)
                return
            # 并发护栏：同一 (pid, phase) 已有 agent 在跑就拒绝，别双开互相覆盖产物/代码
            with _STAGE_RUN_LOCK:
                if (pid, phase) in _STAGE_RUNNING:
                    self._json({"error": "already_running"}, 409)
                    return
                _STAGE_RUNNING.add((pid, phase))
            instruction = (data.get("instruction") or "").strip()
            note = f"让 Agent 做阶段{phase}「{_STAGE_NAME[phase]}」" + (f"（要求：{instruction}）" if instruction else "")
            with open(os.path.join(pf, "inbox.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": _now(), "from": "web", "type": "stage-request",
                                    "text": note}, ensure_ascii=False) + "\n")
            threading.Thread(target=_auto_stage, args=(pf, phase, instruction, pid), daemon=True).start()
            self._json({"ok": True})
            return
        if sub == "/api/deploy-creds":
            # 用户在⑦填部署凭证（SSH 地址/账号/token…）：存到项目仓库外的 secrets/<id>.env(600)。
            # 默认与已存的合并；replace=true 整体覆盖；clear=true 清空全部；remove=KEY 删单条。
            if data.get("clear"):
                n = _save_deploy_creds(pid, {})
                self._json({"ok": True, "count": n})
                return
            rm = data.get("remove")
            if rm:
                cur = _load_deploy_creds(pid)
                cur.pop(str(rm), None)
                n = _save_deploy_creds(pid, cur)
                self._json({"ok": True, "count": n})
                return
            creds = data.get("creds")
            if not isinstance(creds, dict):
                self._json({"error": "bad_creds"}, 400)
                return
            if data.get("replace"):
                merged = creds
            else:
                merged = _load_deploy_creds(pid)
                merged.update(creds)
            n = _save_deploy_creds(pid, merged)
            self._json({"ok": True, "count": n})
            return
        if sub == "/api/choice":
            # 用户点选/补充答复一条 Agent 抛来的待确认问题
            cid = data.get("id")
            answer = data.get("answer")
            cpath = os.path.join(pf, "choices.json")
            try:
                with open(cpath, encoding="utf-8") as f:
                    cdata = json.load(f)
                if not isinstance(cdata, dict):
                    cdata = {"choices": []}
            except (FileNotFoundError, json.JSONDecodeError):
                cdata = {"choices": []}
            found = None
            for ch in cdata.get("choices", []):
                if ch.get("id") == cid:
                    ch["answer"] = answer
                    found = ch
            _atomic_write_json(cpath, cdata)
            if found:
                with open(os.path.join(pf, "inbox.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": _now(), "from": "web", "type": "choice-answer",
                                        "text": f"已确认：{found.get('question', '')} → {answer}"},
                                       ensure_ascii=False) + "\n")
            self._json({"ok": True})
            return
        text = (data.get("text") or "").strip()
        if not text:
            self._json({"error": "empty"}, 400)
            return
        msg = {"ts": _now(), "from": "web", "text": text}
        msg.update({k: v for k, v in data.items() if k not in ("ts", "from", "text")})
        with open(os.path.join(pf, "inbox.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self._json({"ok": True})


def _health_sweep() -> None:
    for reg in _registry_entries():
        try:
            if reg.get("archived"):
                continue
            path = reg.get("path") or ""
            pf = os.path.join(path, ".productflow")
            if not os.path.isdir(pf):
                continue
            try:
                deploy = _read_json(os.path.join(pf, "deploy.json"))
            except Exception:
                continue
            url = deploy.get("url")
            if not url:
                continue
            ok, status, ms = False, None, None
            t0 = time.monotonic()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": f"productflow-health/{VERSION}"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    status = resp.status
                ms = int((time.monotonic() - t0) * 1000)
                ok = 200 <= status < 400
            except urllib.error.HTTPError as e:
                status = e.code
                ms = int((time.monotonic() - t0) * 1000)
            except Exception:
                pass
            _atomic_write_json(os.path.join(pf, "health.json"), {
                "url": url, "ok": ok, "status": status, "ms": ms, "checked": _now(),
            })
        except Exception:
            continue


def _health_loop() -> None:
    while True:
        try:
            _health_sweep()
        except Exception:
            pass
        time.sleep(300)


def _probe_version(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version", timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _register_dir(path: str) -> None:
    """--dir 顺手注册：从项目 state.json 取 id 后 upsert 注册表条目。"""
    try:
        state = _read_json(os.path.join(path, ".productflow", "state.json"))
        pid = state.get("id")
        if not (isinstance(pid, str) and ID_RE.match(pid)):
            print(f"note: {path} has no project id (run pf_state there to self-heal); skipped registration")
            return
        entry_path = os.path.join(PROJECTS_DIR, pid + ".json")
        entry = {"id": pid, "path": path, "created": _now(), "archived": False, "v": 1}
        try:
            old = _read_json(entry_path)
            entry["created"] = old.get("created") or entry["created"]
            entry["archived"] = bool(old.get("archived"))
        except Exception:
            pass
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        _atomic_write_json(entry_path, entry)
        print(f"registered {pid} -> {path}")
    except Exception as e:
        print(f"note: failed to register {path}: {e}")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="productflow-server")
    p.add_argument("--dir", default=None, help="optional: register this project dir, then serve all projects")
    p.add_argument("--port", type=int, default=7717)
    p.add_argument("--open", action="store_true", help="open browser after start")
    args = p.parse_args(argv)

    os.makedirs(PROJECTS_DIR, exist_ok=True)
    os.makedirs(PENDING_DIR, exist_ok=True)
    if args.dir:
        _register_dir(os.path.abspath(args.dir))

    url = f"http://127.0.0.1:{args.port}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        info = _probe_version(args.port)
        if info and info.get("app") == "productflow":
            print(f"already running (version {info.get('version')}) at {url}")
            return 0
        print(f"error: port {args.port} is taken by something that is not a ProductFlow v2 server\n"
              f"(maybe an old ProductFlow or another app). Inspect with: lsof -ti:{args.port}",
              file=sys.stderr)
        return 1

    threading.Thread(target=_health_loop, daemon=True).start()
    threading.Thread(target=_refresh_latest, daemon=True).start()   # 启动即后台拉一次远端版本（不阻塞启动）
    print(f"ProductFlow console: {url}  (home: {PF_HOME})  v{VERSION}")
    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
