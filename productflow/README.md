# ProductFlow

把"做一个互联网产品"变成一条可视化流水线——从落地页、官网，到带数据库与后端的功能性 Web 应用（落地页只是最简单的一种）：**市场调研 → 设计 → 功能与数据(ER/DDL/API) → 前后端开发+测试 → 部署上线**。装上后说一句"做一个 XX"，AI 就启动一个 localhost 操作台并逐阶段推进；你既能在 CLI 对话，也能在网页操作台看进度、圈选方案、留言。

> 这份 README 面向**安装/接手本 skill 的人**。AI 执行时读的是 `SKILL.md`（编排）+ `references/`（各阶段手册）。

## 安装

把整个 `productflow/` 目录放进 agent 的 skills 目录即可：

- **Claude Code**：`~/.claude/skills/productflow/`（或项目内 `.claude/skills/`、插件市场）。SKILL.md 的 frontmatter 让它按需自动加载。
- **Codex / 其它无 Skill 机制的 agent**：见本目录的 **`AGENTS.md`**——它是去掉 Claude 专属 frontmatter 的引导版，把其内容并入你 agent 的指令文件（Codex 读 `AGENTS.md`）。脚本目录原样放置即可：`pf_state.py` / `server.py` 纯 Python 标准库、用 `__file__` 自定位，agent-中立。手册里"调用 X skill""Agent Teams"等 Claude 专属说法，按 SKILL.md「依赖表 + agent-中立总则」降级为手动做。

## 前置依赖

| 依赖 | 必需性 | 说明 |
|------|--------|------|
| **Python 3** | 必需 | 操作台 server + 状态机，仅用标准库，无需 pip 安装任何包 |
| **Node.js + npm** | 视项目 | 仅 T2/T3（带后端）项目需要；纯静态落地页(T1)不需要 |
| **Playwright** | 强烈建议 | 竞品截图、成品预览、E2E 测试都靠它。`pip install playwright && python3 -m playwright install chromium`，或 `npm i -D @playwright/test && npx playwright install chromium` |
| Docker | 可选 | 仅当用户要本地/容器化部署 T3 时 |
| 增强型 skill | 可选 | design-taste-frontend、openai-image-gen、database-schema-designer、deploy-cf-pages 等——**没有会自动降级**，不影响流程跑通（降级方案见 `SKILL.md` 依赖表） |

**本 skill 不内置任何 API key**，也不绑定任何特定服务器或网关。需要图像生成（设计阶段参考图）时由 openai-image-gen skill 自带其 key 配置；部署目标机由用户在 Phase 5 提供。

## 启动（AI 会自动做，这里说明机制）

```bash
SKILL_DIR=<本目录的绝对路径>           # Claude Code 下通常 ~/.claude/skills/productflow
# 1. 探活；无响应才拉起全局操作台（nohup 脱离 shell，否则 agent 工具调用结束即被杀）
curl -s http://127.0.0.1:7717/api/version \
  || nohup python3 "$SKILL_DIR/scripts/server.py" >/tmp/productflow-server.log 2>&1 &
# 2. 新建项目（export 一次 PF_PROJECT，后续 pf_state 命令免带 --dir）
export PF_PROJECT=~/code/<产品slug>
mkdir -p "$PF_PROJECT" && python3 "$SKILL_DIR/scripts/pf_state.py" init --product "<产品名>"
```

server **不会自动弹浏览器**——手动打开 `http://127.0.0.1:7717/` 看项目卡片墙，`/p/<id>/` 进单项目的看板 + 无限画布。远程服务器场景先 `ssh -L 7717:127.0.0.1:7717 user@server` 端口转发（server 只 bind 127.0.0.1）。

> 注意：agent 的每个 Bash 工具调用通常是独立 shell，`export` 不跨调用持久——每个跑脚本的 Bash 块开头都要重设 `SKILL_DIR`/`PF_PROJECT`。

## 目录结构

```
productflow/
├── SKILL.md              # 主编排（AI 入口）
├── README.md             # 本文件（安装说明）
├── scripts/
│   ├── pf_state.py       # 流水线状态机 CLI（init/phase/step/artifact/log/inbox/reply/...）
│   └── server.py         # localhost 操作台（多项目卡片墙 + 看板 + 无限画布 + 健康监控）
├── assets/
│   ├── console.html      # 操作台前端（暗色双视图）
│   └── vendor/           # markmap 本地副本（思维导图渲染，离线可用）
└── references/
    ├── phase-1-research.md   # 竞品调研 + 核心矛盾分析导图
    ├── phase-2-refs.md       # 找参考（Dribbble 参考，供挑选）
    ├── phase-3-hero.md       # 首图设计（按参考生成首图、定视觉基调）
    ├── phase-4-pages.md      # 页面设计（所有页面 × 平台）→ direction.md 定稿
    ├── phase-5-spec.md       # 模块/ER/DDL/API/选模板
    ├── phase-6-frontend.md   # 脚手架/前端实现/本地预览（无后端时含单元+集成测试）
    ├── phase-7-backend.md    # 后端实现/单元+集成测试/接口文档（无后端项目跳过）
    ├── phase-8-deploy.md     # CF Pages / Workers / 单机(Docker 或 systemd)
    └── templates.md          # 三个固定开发模板 T1/T2/T3
```

状态与产物写在**每个目标项目**的 `.productflow/` 下（不在 skill 目录里）；全局注册表在 `~/.productflow/projects/`。

## 跨平台说明

**macOS / Linux**：已验证，即装即用。

**Windows**：状态机的文件锁依赖 Unix 的 `fcntl`，已包成可降级（Windows 上退化为单进程无锁，功能可用但并发安全降级）。但默认路径（`~/code`、`~/.productflow`）和 Docker bind mount 行为未在 Windows 上测试，建议在 WSL 里跑。
