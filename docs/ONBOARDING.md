# ProductFlow 上手指南（新人 Onboarding）

> 目标：让一个新工程师在**半小时内**跑起来、看懂代码在哪、并能安全地做第一个改动。
> 深入架构见 [`ARCHITECTURE.md`](./ARCHITECTURE.md)；业务流程见 [`DOMAIN.md`](./DOMAIN.md)；
> 交互式代码地图跑 `/understand-dashboard`（读 `.understand-anything/knowledge-graph.json`）。

---

## 0. 5 分钟建立心智模型（最重要）

- **这是一个「工具」，不是一个「产品」。** 本仓库是一套 Claude Code skill + 一个本地操作台，用来把「做互联网产品」变成 7 阶段流水线。你在代码里**不会**看到某个具体产品——只有流水线的编排、操作台后端、前端源码。
- **双入口 + 单一状态源**：用户既能在 CLI 跟 agent 对话（主通道），也能开网页操作台（`localhost:7717`）看进度/圈选/留言。两边共享同一份 `<project>/.productflow/state.json`。
- **Agent 是执行者**：Claude 读手册干活，每一步用 `pf_state.py` 写状态；网页端经 WebSocket 实时刷新。**不写状态 = 网页上看不到进展。**
- **工具与用户数据分离**：工具在本仓库；用户产出的产品数据在 `~/.productflow/`（注册表/队列/密钥）+ `~/code/<slug>/`（项目）。所以更新工具（`git pull`）不碰用户数据。

一句话流水线：

```
①市场调研 → ②找参考 → ③首图设计 → ④页面设计 → ⑤功能与数据设计 → ⑥开发实现 → ⑦部署上线
```

---

## 1. 前置依赖

| 依赖 | 必需性 | 说明 |
|------|--------|------|
| **Python 3.8+** | 必需 | 操作台 server + 状态机，仅标准库、零 pip 依赖 |
| **Claude Code（`claude`）** | 必需（运行时） | 流水线靠 `claude -p` 跑各阶段 agent；跑测试时用沙箱 stub 顶替 |
| **openai-image-gen + OpenAI 生图 key** | 必需（进 ③④ 时） | `gpt-image-2` 出图；key 放 `~/.config/openai/env` |
| **Node.js + npm** | 仅开发前端要 | 改 `web/` 源码才需要；用户端不跑 Node |
| Playwright + chromium | 可选（建议） | ②找参考截图 / e2e 测试；缺了相关用例自动 skip |
| Docker | 可选 | ⑦本地部署用到再装 |

> 本仓库的**测试与后端只依赖 Python 标准库**。想快速验证「装对了」，跑一遍测试即可（见 §5）。

---

## 2. 起步：跑起来（两条路）

**A. 只想看操作台长什么样**（不跑真流水线）：

```bash
# 从仓库根目录
python3 productflow/scripts/server.py &     # 拉起 7717（前台会阻塞，用 & 或 nohup）
# 浏览器打开 http://127.0.0.1:7717/
```

server 只 bind `127.0.0.1`。远程机器需 `ssh -L 7717:127.0.0.1:7717 user@host` 端口转发。

**B. 完整体验**（作为 Claude Code skill）：把带 `SKILL.md` 的目录软链进 `~/.claude/skills/`，再在 Claude Code 里说「做一个 XXX 网站」。装法见根 `README.md`。开发时一般用 A。

---

## 3. 仓库地图（我该去哪改）

```
productflow/                  ← 主 skill（90% 的后端/编排改动在这里）
├── SKILL.md                  编排大脑：7 阶段协议、状态协议、检查点节奏、降级表
├── AGENTS.md                 SKILL.md 的 Codex 版（改编排要同步）
├── references/phase-N-*.md   每个阶段的操作手册（步骤 ID / 产物清单 / 要调的 skill）
├── scripts/
│   ├── pf_state.py           状态机 CLI —— 所有进度写 state.json
│   ├── server.py             操作台 HTTP+WS server（单文件，2496 行）
│   ├── edit.py               图像编辑/inpaint 辅助
│   ├── migrate.py            state.json 数据迁移
│   ├── appstore_shots.py     App 商店截图辅助
│   ├── setup.py / doctor.py  自检 / 深度体检
│   └── start.sh / update.sh  启动 / 更新
├── assets/dist/              React 操作台**构建产物**（由 web/ 生成，必须提交）
├── assets/console.html       零构建 HTML 回退
└── tests/                    Python 测试（见 §5）

web/                          ← 操作台前端源码（改 UI 来这里）
├── src/App.tsx  store.ts  bus.ts  types.ts  lib.ts
├── src/components/*.tsx      20+ 组件（Board/Canvas/Stepper/ChatDrawer…）
└── src/screens/Home.tsx      卡片墙

openai-image-gen/             ← 生图引擎 skill（③④ 调用）
landing/                      ← 工具官网落地页（静态，和流水线无关）
productflow-{init,start,update,doctor,adversarial-e2e}/   ← 5 个配套命令 skill
docs/                         ← 本套分析文档
```

**决策速查**：改流水线步骤/产物 → `productflow/SKILL.md` + 对应 `references/phase-N-*.md`；改状态字段/命令 → `pf_state.py`；改操作台接口/后台逻辑 → `server.py`；改网页 UI → `web/src/`（改完必须 build）。

---

## 4. 三条开发回路

### 4.1 后端 / 状态机（Python）

直接改 `productflow/scripts/*.py`，然后跑对应测试（见 §5）。三大脚本纯标准库、靠 `__file__` 自定位，无需装包。

> **陷阱**：每个 Bash 调用是独立 shell，`export` 不跨调用持久。写脚本/文档示例时，凡跑 `pf_state.py` 的块都要重设 `SKILL_DIR` / `PF_PROJECT`。

### 4.2 前端（`web/`）

```bash
cd web
npm install
npm run dev        # vite 热更开发（连本地 7717 的 API）
npm run typecheck  # tsc --noEmit
npm run build      # → 输出 ../productflow/assets/dist
```

> **铁律**：改完 React 源码**必须 `npm run build` 并提交 `productflow/assets/dist`**——用户机器不跑 Node，只读这份预编译产物。漏提交 = 用户看不到你的改动。

### 4.3 编排（skill 正文）

改 `SKILL.md`/`references/*` 是「改 agent 的行为」。要点：① `SKILL.md` 与 `AGENTS.md` 正文一致（双轨）；② 新增依赖要给降级路径，不硬报错；③ 版本号三处同步（见 §6）。

---

## 5. 测试（改完必跑）

```bash
cd productflow
python3 -m unittest discover -s tests -p 'test_*.py' -v   # 全量
tests/run.sh -v                                           # 包装器（暴露 ResourceWarning）

# 单个
python3 -m unittest tests.test_pf_state -v
python3 -m unittest tests.test_server.ServerTest.test_version
```

- **纯 stdlib `unittest`**，零三方依赖。
- **隔离**：测试走 subprocess + 覆盖 `HOME` 环境变量，把注册表/队列/新项目全沙箱进临时目录，**绝不碰真实 `~/.productflow`**；`helpers.py` 放 no-op `claude` stub 避免烧 token。
- **分层**：CLI + HTTP 层必须永远绿；e2e 层（`test_e2e_*.py`，headless chromium）缺 playwright 时**自动 skip**。
- ⚠️ **别动 `helpers._env()`** 里注回 user-site 的那段——它保证沙箱下仍能找到 `pip --user` 装的 Pillow/playwright（详见 `ARCHITECTURE.md` §11）。

---

## 6. 提交约定（关键不变量）

1. **版本号三处同步**：`productflow/VERSION`、`productflow/SKILL.md` frontmatter `version:`、commit message 里的 `(x.y.z)`。
2. **提交信息**：`feat(scope): 描述 (版本号)`，scope 常用阶段编号或 `console`/`redraw`/`board`。
3. **改前端必带 dist**：源码改动 + `assets/dist` 构建产物同一个 commit。
4. **SKILL.md ↔ AGENTS.md 同步**。

---

## 7. 建议的第一个改动（练手）

由浅入深，每个都能独立验证：

1. **读一遍**：`docs/ARCHITECTURE.md` + 跑 `/understand-dashboard` 点开知识图谱，对着 13 步导览走一遍。
2. **加一条状态字段的单元测试**：在 `tests/test_pf_state.py` 里挑一个 `cmd_*` 加一个 case，`python3 -m unittest tests.test_pf_state` 让它绿。
3. **给某个阶段手册补一句**：在 `references/phase-N-*.md` 里补一个你觉得缺的边界说明（纯文档，零风险）。
4. **前端小改 + build**：在某个组件调个文案/样式，`npm run build`，刷新 7717 看到效果，确认「改源码→build→提交 dist」这条回路通了。

---

## 8. 上手避坑清单（贴墙版）

- [ ] 跑 `pf_state.py` 的 shell 块开头重设 `SKILL_DIR` / `PF_PROJECT`
- [ ] `choice wait` 退出码恒为 0，**解析 stdout JSON** 判超时，别用 `$?`
- [ ] 改 `web/` 后 **`npm run build` 并提交 `assets/dist`**
- [ ] 进 ③④ 前确认生图 key 就绪（`~/.config/openai/env`），缺了向用户要、别静默降级
- [ ] 版本号三处同步；`SKILL.md` 与 `AGENTS.md` 同步
- [ ] 操作台只 bind `127.0.0.1`，别部署公网；密钥不进 git/日志/产物
- [ ] 新增依赖给降级路径，不硬报错/硬装
- [ ] 别在测试里 in-process import `pf_state`/`server`；别碰真实 `~/.productflow`
- [ ] `针对这个项目的需求改造/` 是同事的需求改造文件夹，不是工具本体
```
