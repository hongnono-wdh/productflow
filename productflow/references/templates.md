# templates.md — 固定开发模板规范

在 Phase 5 的 pick-template 步骤、Phase 6 的 scaffold 步骤、Phase 7 的 pick-target 步骤开始前读本文件。

ProductFlow 只有三个模板，技术选型全部锁死、不给备选——"固定模板"的意义就是消除选择成本：
agent 不在框架之间摇摆，用户不被无关决策打断。确需偏离时按文末"偏离协议"执行。

## 选型决策树

```
需要 admin 后台 / 登录 / 自有服务器上跑长期服务？
├─ 是 → T3 landing-fullstack
└─ 否 → 需要持久化数据（waitlist / 订阅 / 计数 / 留言）？
    ├─ 是 → T2 landing-worker
    └─ 否 → T1 static-landing（纯展示，表单走第三方或 Pages Functions）
```

拿不准时往简单的选：T1 升 T2、T2 升 T3 都只是加目录，不用推翻前端。

## 通用规则（三个模板共用）

- 落地页本体一律用 design-taste-frontend 设计实现；只有 T3 的 admin 界面用 frontend-design 或 ui-ux-pro-max。
- Phase 5 产物是唯一事实来源：schema 以 artifacts/phase-5/schema.sql 为准（复制进项目，不重写）；API 以 artifacts/phase-5/ 下的接口契约为准，端点一条不多、一条不少。
- 目录树是合同：Phase 6 scaffold 按树建骨架，不加树之外的目录；测试与部署脚本按各模板小节写。
- 选定模板后立即写 artifacts/phase-5/template-choice.md（选了哪个、决策树走了哪条分支、一句话理由）并 artifact 登记。

---

## T1 static-landing

**适用**：纯展示型落地页——产品介绍、定价、FAQ，最多收一个邮箱。没有需要查询的数据。

**选型（锁死）**：HTML + CSS + vanilla JS，零框架、零构建步骤。
理由：落地页的命门是首屏速度和可维护性；没有构建链就没有构建故障，CF Pages 直接托管静态目录即是生产环境。表单提交走 Cloudflare Pages Functions（或 Formspree 这类第三方），不为一个表单架后端。

```
my-product/
├── .productflow/            # 状态与产物（协议目录，勿手改 state.json）
├── public/                  # 部署根目录
│   ├── index.html
│   ├── css/style.css
│   ├── js/main.js
│   └── assets/              # 图片、favicon、og-image
├── functions/               # 可选：仅当有表单时
│   └── api/subscribe.js     # Pages Function，POST 收表单
└── README.md
```

**与 Phase 5 的衔接**：T1 无数据库——er-diagram 与 schema-ddl 两步标 skipped（逐字执行）：
```
python3 "$SKILL_DIR/scripts/pf_state.py" step 5 er-diagram --status skipped
python3 "$SKILL_DIR/scripts/pf_state.py" step 5 schema-ddl --status skipped
```
接口契约若只有一个表单端点，实现就在 functions/api/subscribe.js。

**Phase 7 部署**：用 deploy-cf-pages skill；命令核心是 `npx wrangler pages deploy public`。

**不做什么**：不引 React/Vue/Tailwind，不加打包器和 npm 依赖，不做 SPA 路由，不写独立后端服务，不为"未来可能的功能"留空壳目录。

---

## T2 landing-worker

**适用**：落地页 + 轻量数据写入——waitlist、订阅、访问统计、简单留言。有数据但没有人要登录后台看复杂报表。

**选型（锁死）**：静态前端 + Cloudflare Worker（vanilla fetch handler）+ D1。
理由：D1 就是 SQLite，Phase 5 的 schema.sql 不经翻译直接导入；Worker 免运维、免费额度覆盖落地页量级；一个 Worker 同时托管静态资源和 API，部署面只有一个。

```
my-product/
├── .productflow/
├── public/                  # 静态前端，由 Worker assets 托管
│   ├── index.html
│   ├── css/style.css
│   └── js/main.js
├── worker/
│   ├── src/index.js         # 全部 API 路由都实现在这一个文件
│   └── schema.sql           # 从 artifacts/phase-5/schema.sql 复制而来
├── wrangler.toml
└── README.md
```

wrangler.toml 最小配置（database_id 取 `npx wrangler d1 create my-product-db` 的输出）：
```toml
name = "my-product"
main = "worker/src/index.js"
compatibility_date = "2026-06-01"

[assets]
directory = "public"

[[d1_databases]]
binding = "DB"
database_name = "my-product-db"
database_id = "<d1 create 输出的 id>"
```

**与 Phase 5 的衔接**：
- artifacts/phase-5/schema.sql → 复制为 worker/schema.sql，本地导入 `npx wrangler d1 execute my-product-db --local --file=worker/schema.sql`。
- 接口契约的每个端点 → worker/src/index.js 中按 `url.pathname` 分支实现，D1 绑定名固定为 `DB`。

**Phase 7 部署**：`npx wrangler deploy`；上线前先对远端库执行同一份 schema：
`npx wrangler d1 execute my-product-db --remote --file=worker/schema.sql`。smoke-test 用 curl 打每个 API 端点 + browse 截首页。

**不做什么**：不引 Hono/itty-router（端点 ≤5 个，if/switch 足够），不加 ORM，不做用户认证（waitlist 不需要），不拆多个 Worker，不建 KV/R2（D1 一个就够）。

---

## T3 landing-fullstack

**适用**：需要 admin 后台（看报名名单、导出数据、改内容）、需要登录，或用户明确要部署在自有服务器上。

**选型（锁死）**：Node.js 20 + Express + better-sqlite3 + 静态前端，测试用内置 node:test。
理由：better-sqlite3 同步 API 没有回调地狱，单文件数据库免数据库运维，与 schema.sql 直接兼容；Express 是最无惊喜的选择；单机部署用 systemd（裸机）或 Docker compose（项目含 Dockerfile）托管一个 node 进程，运维路径最短。

```
my-product/
├── .productflow/
├── public/                  # express.static 托管
│   ├── index.html           # 落地页（design-taste-frontend）
│   ├── admin/index.html     # 后台（frontend-design / ui-ux-pro-max）
│   ├── css/
│   └── js/
├── server/
│   ├── app.js               # Express 入口，监听 PORT（默认 3000）
│   ├── routes/api.js        # 全部 API 路由都实现在这一个文件
│   ├── db.js                # better-sqlite3 初始化，启动时 exec schema.sql
│   └── schema.sql           # 从 artifacts/phase-5/schema.sql 复制而来
├── data/                    # app.db 落盘目录（写入 .gitignore）
├── tests/
│   ├── api.test.js          # node:test，覆盖每个 API 端点
│   └── e2e/journeys.spec.cjs # @playwright/test，用户旅程（auth 全循环等，见 phase-6）
├── Dockerfile               # 可选：用户要 Docker/本地部署时
├── docker-compose.yml       # 可选：配 .dockerignore 排除 node_modules
├── .env.example
├── package.json
└── README.md
```

**与 Phase 5 的衔接**：
- artifacts/phase-5/schema.sql → 复制为 server/schema.sql，db.js 启动时 `db.exec(...)` 建表（CREATE TABLE IF NOT EXISTS 风格，schema-ddl 步骤产出时即按此写）。
- 接口契约的每个端点 → server/routes/api.js；admin 鉴权用单一 ADMIN_TOKEN 环境变量 + Bearer 头，不上 session/OAuth。

**Phase 7 部署**（单机：任意 Linux 服务器或本机；目标机由用户提供）：项目含 Dockerfile 时优先 `docker compose up -d --build`；否则 rsync 代码到 /opt/my-product → `npm ci --omit=dev` → 写 systemd unit（ExecStart=node server/app.js，Restart=on-failure，Environment=PORT/ADMIN_TOKEN）→ `systemctl enable --now`。需要域名时 caddy 反代（自动 https，见 phase-7-deploy.md 路径 C），否则直接裸端口验收。

**不做什么**：不上 PostgreSQL/MySQL，不上 TypeScript 构建，不用 PM2（systemd 或 Docker 重启策略够了），admin 前端不引框架（vanilla JS + fetch 渲染表格即可），不做多环境配置体系（一个 .env 示例足够）。Docker 非必须，但用户要本地/容器化部署时是首选形态——务必带 `.dockerignore` 排除宿主 node_modules，SQLite 用 `journal_mode=DELETE`（见 phase-6 实战教训）。

---

## 偏离协议

模板技术栈默认不可替换。只有当需求与三个模板都硬冲突（例如用户指名要某框架、或需要 WebSocket 长连接）才允许偏离，且：
1. 在 artifacts/phase-5/template-choice.md 写明：基于哪个模板、改动哪一项、为什么三个原始模板都不满足；
2. 偏离只许替换冲突项，目录结构与其余选型仍按最近的模板执行；
3. CLI 里向用户明示偏离点，得到确认再进 Phase 6。

## 检查点

- Phase 5 选型完成时（逐字执行）：
```
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 5 artifacts/phase-5/template-choice.md --title "模板选择与理由"
python3 "$SKILL_DIR/scripts/pf_state.py" step 5 pick-template --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "选定模板 T2 landing-worker（按实际替换）"
```
- Phase 6 scaffold 完成时：目录树与本文件一致、schema.sql 已复制进项目并能成功建表，然后
  `python3 "$SKILL_DIR/scripts/pf_state.py" step 6 scaffold --status done`。
- Phase 7 开始时：部署路径由模板决定，不再询问用户选哪条；确认后
  `python3 "$SKILL_DIR/scripts/pf_state.py" step 7 pick-target --status done`。
- 每阶段收尾前照例先跑 `python3 "$SKILL_DIR/scripts/pf_state.py" inbox` 读网页端消息，并逐条 `python3 "$SKILL_DIR/scripts/pf_state.py" reply "<回应>"` 后再继续。
