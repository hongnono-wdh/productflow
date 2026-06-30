# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这是什么

ProductFlow 是一个 **Claude Code skill 集合**：把"做一个互联网产品"变成 7 阶段可视化流水线（①市场调研 →②找参考 →③首图设计 →④页面设计 →⑤功能与数据设计 →⑥开发实现 →⑦部署上线），配一个跑在 `localhost:7717` 的本地操作台。产出范围从落地页/官网到带数据库后端的 Web 应用，再到原生移动 App（iOS SwiftUI / Android Compose）和 PC 桌面应用（Tauri）。

关键点：**本仓库是工具本身**（skill + 操作台），不是用它生产出来的产品。用户装它时通过 `for s in */; do [ -f "$s/SKILL.md" ] && ln -sfn ...` 把每个带 `SKILL.md` 的目录软链进 `~/.claude/skills/`。用户的产品数据落在 skill 之外（`~/.productflow/` + `~/code/<slug>/`），所以 `git pull` 不会碰用户数据。

## 仓库布局

每个顶层目录要么是一个 skill（有 `SKILL.md`），要么是支撑代码：

| 目录 | 角色 |
|------|------|
| `productflow/` | **主 skill**：`SKILL.md`（编排）+ `references/phase-N-*.md`（各阶段手册）+ `scripts/`（Python 后端）+ `assets/dist`（React 操作台构建产物）+ `assets/console.html`（零构建回退）+ `tests/` |
| `web/` | 操作台的 **React + TS 源码**（Vite）。构建产物提交进 `productflow/assets/dist`——**端上零 Node**，用户机器只跑 Python |
| `openai-image-gen/` | ③④ 阶段的 AI 生图引擎 skill（随仓库一起装、被主 skill 调用） |
| `productflow-init/start/update/doctor/adversarial-e2e/` | 5 个配套命令 skill，每个只有一个 `SKILL.md`，正文里委托给 `productflow/scripts/*` |
| `landing/` | 工具自己的落地页（纯静态 `index.html`，部署在 pf.gjs.ink），与流水线无关 |

## 架构核心

**双入口 + 单一状态源。** 用户既能在 CLI 对话（主通道），也能在网页操作台操作；两边共享 `<project>/.productflow/state.json`。Agent（你）是流水线的执行者。

三个支柱（都在 `productflow/scripts/`，**纯 Python 3 标准库、零三方依赖**，靠 `__file__` 自定位）：

- **`pf_state.py`** — 状态机 CLI。所有进度（阶段/步骤/产物/日志/留言/choice/页面地图）都通过它写进 `state.json`。**不调用它 = 操作台上看不到任何进展**。
- **`server.py`** — 操作台 HTTP + WebSocket 服务（**单文件 ~130KB**），全局单例固定端口 7717，只 bind `127.0.0.1`。一个进程服务所有项目。`/api/version`、`/api/projects`、`/api/create`、`/api/pending` 等。在 brief/explore 请求上会后台自动 spawn 真 `claude` agent（`_auto_gen_brief` / `_auto_explore`）。
- **`PF_HOME = ~/.productflow`**（import 时计算）— 全局注册表 + pending 队列 + 部署密钥（`secrets/<id>.env`，600 权限，不进 git）。新项目默认建在 `~/code/<slug>/`。

操作台前端有两套：`assets/dist`（React 主力）和 `assets/console.html`（零构建回退）。`server.py` 同时能服务二者。

**Agent 执行模式（写代码/脚本时要知道）**：每个 Bash 工具调用是独立 shell，`export` 不跨调用持久。所以每个跑 `pf_state.py` 的 Bash 块开头都要重设 `SKILL_DIR` 和 `PF_PROJECT`。`choice wait` 的退出码恒为 0，必须解析 stdout JSON 判断超时（不能靠 `$?`）。

## 常用命令

### 操作台前端（`web/`，开发时用）
```bash
cd web
npm install
npm run dev        # vite 开发服务器（热更）
npm run build      # 构建 → 输出到 ../productflow/assets/dist（必须提交）
npm run typecheck  # tsc --noEmit
```
改完 React 源码后 **必须 `npm run build` 并提交 `productflow/assets/dist`**——用户机器不跑 Node，只读这份产物。Vite `base: '/dist/'` 让哈希资源 URL 在 `/` 和 `/p/<id>/` 两种路由下都能解析。

### Python 测试（`productflow/tests/`）
```bash
cd productflow
python3 -m unittest discover -s tests -p 'test_*.py' -v   # 全量
tests/run.sh                                              # 包装器（-W default 暴露 ResourceWarning）
tests/run.sh -v

# 单个模块 / 类 / 测试
python3 -m unittest tests.test_pf_state -v
python3 -m unittest tests.test_server.ServerTest.test_version
```
测试纯 `stdlib unittest`。**隔离机制**：`pf_state.py`/`server.py` 都在 import 时算 `~/.productflow`，所以测试用 `helpers.make_home()` 覆盖 `HOME` 环境变量，把注册表/队列/新项目目录全部沙箱进临时目录。`helpers.py` 还在沙箱 `HOME/bin` 放一个 no-op `claude` stub，避免测试真烧 token。CLI + HTTP 层必须永远绿；e2e 层（`test_e2e_*.py`，headless chromium via playwright）在缺 playwright/chromium 时**自动 skip**。所有测试走 subprocess + `HOME` 覆盖，绝不 in-process import `pf_state`/`server`，也绝不碰真实 `~/.productflow`。

**反直觉点**：`HOME` 覆盖会顺带让子进程把 user-site 算到沙箱 `HOME` 下，丢掉 `pip install --user` 的依赖（Pillow/playwright），导致 redraw 等用例假阳性失败。`helpers._env()` 在 import 时用真实 `HOME` 抓 `site.getusersitepackages()`，再注回子进程的 `PYTHONPATH` 补救——既不削弱数据隔离，又和真实（未覆盖 `HOME`）运行看到的依赖一致。写新测试时别动这段。

### 自检与启动
```bash
python3 productflow/scripts/setup.py    # = /productflow-init：查依赖 + 跑测试
sh productflow/scripts/start.sh         # = /productflow-start：拉起 7717 操作台
python3 productflow/scripts/doctor.py   # 深度自检（含真调生图批量出 2 张）
```

### 对抗式 e2e（`productflow/tests/e2e-adversarial/`，后台 QA）
**双环双进程**，互不阻塞、靠 `findings/findings.jsonl` 交接：
- **Loop 1（发现）** `sh loop1-discovery.sh`——轮转 8 个 persona，各自跑 `harness.py` 对**独立沙箱 server + 浏览器**（多实例，绝不碰 :7717），把问题以 `status=open` 追加进 findings，**只记不修**。`touch findings/.stop` 停。
- **Loop 2（修复）** 由 `/loop` 提示词驱动：读 `python3 findings.py open`，逐条修代码、`mark` 成 fixed/wontfix 并附 `fix_commit`。
- 两进程靠 `findings.py` 里的 `fcntl` 跨进程锁安全并发读改写。`python3 findings.py` 看汇总。

## 改动须知

- **版本号有多处要同步**：`productflow/VERSION`、`productflow/SKILL.md` 的 frontmatter `version:`、commit message 里的 `(x.y.z)`。提交信息遵循 `feat(scope): 描述 (版本号)` 约定（见 git log），scope 常用阶段编号或 `console`/`redraw`/`board` 等。
- **skill 正文双轨**：`SKILL.md`（Claude Code，带 YAML frontmatter 自动加载）与 `AGENTS.md`（Codex 等无 Skill 机制的 agent）正文一致，以 `SKILL.md` + `references/` 为准。改编排逻辑要顾及两边。
- **核心流水线是 agent-中立的**：`pf_state.py` / `server.py` 拷到别处直接能跑。编排层里"调用 X skill"对无 Skill 机制的 agent 当方法论名词降级（见 `AGENTS.md` 与 SKILL.md「优雅降级」表）。新增依赖要给降级路径，不要硬报错或硬装。
- **进阶段前先读对应 `references/phase-N-*.md`**——里面有步骤 ID、产物清单和要调的既有 skill，不要凭记忆做。
- **边界**：操作台只 bind `127.0.0.1`，不要部署到公网；复刻竞品只学结构/信息架构/风格，不抄文案/盗图/复制品牌；部署密钥走 `~/.productflow/secrets/`，绝不打印进日志/产物/留言。
