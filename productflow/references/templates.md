# templates.md — 开发栈预设与选型规范

在 Phase 5 的 pick-template 步骤、Phase 6 的 scaffold 步骤、Phase 7 的 pick-target 步骤开始前读本文件。

ProductFlow 做大部分互联网产品——web 站点 / web 应用（落地页只是最简单的一种），以及原生移动 App。
没有"一套模板锁死全部"那回事：**按产品类型/平台选合适的技术栈**。本文件给出各类型的**推荐预设**——它们是减少选择成本的好默认，让 agent 不在框架之间摇摆、用户不被无关决策打断，但**不是唯一选项**：产品确实需要就换栈/换库，在 template-choice.md 写明理由即可（见文末"偏离协议"）。

## 选型：先打包资料，再分析判断（不要替用户锁死）

用户需求五花八门，没有一棵决策树能穷举所有产品形态。所以选型的**第一动作不是套预设，而是打包该产品的可分析上下文，基于资料分析判断最合适的产品形态与技术栈**：

1. **打包可分析上下文**（这一步先做，别跳过）：
   - 平台——`.productflow/wizard.json` 的 `primary`（`PC` / `H5` / `APP`，大写）；
   - `brief.json`——产品定位、目标用户、核心需求；
   - replicate-notes（参考品的信息架构）；
   - `direction.md`（Phase 4 的设计方向）；
   - Phase 5 已产出的功能/数据需求清单（modules.md / er.md / api.md）。
2. **基于这份打包资料分析判断**：这个产品到底是哪种形态、哪套栈最合适——而不是机械往预设里塞。
3. 用户需求多样：除下面列出的预设（P-iOS 原生 iOS / T1·T2·T3 Web），还可能是 **Android、桌面应用（Electron / Tauri / 原生）、浏览器扩展、CLI 工具、小程序、混合形态**等。**预设是常见情况的起点/参考，不是穷举、更不是锁死**——遇到不在预设里的需求，按分析结果选/适配合适的栈，不要硬塞进最接近的预设。
4. 无论命中预设还是另选栈，都在 `artifacts/phase-5/template-choice.md` 写明：**打包了哪些资料 → 分析依据 → 选了什么 / 为什么**（见文末"偏离协议"）。

下面的"选型决策树"是**命中常见情况时的快捷判断**——它接在"打包→分析"之后用，是捷径不是边界。分析后落在它枚举的平台/数据形态里，就照它快速定档；落在它之外，就按上面第 3 条另选。

## 选型决策树（命中常见情况时的快捷判断）

根节点先看**平台**——读 `.productflow/wizard.json` 的 `primary`（`PC` / `H5` / `APP`，大写）；缺失则从 brief.json / 产品定位推断：

```
平台（primary）？
├─ APP（原生移动）→ 原生 App 栈
│   ├─ iOS → P-iOS（SwiftUI + SwiftData，本期实现）
│   └─ Android → 留口子，本期标 TODO（向用户说明暂只交付 iOS，或确认改做 H5）
└─ PC / H5（Web）→ Web 预设，按数据需求选：
    ├─ 需要 admin 后台 / 登录 / 自有服务器上跑长期服务？
    │   └─ 是 → T3 landing-fullstack
    └─ 否 → 需要持久化数据（waitlist / 订阅 / 计数 / 留言）？
        ├─ 是 → T2 landing-worker
        └─ 否 → T1 static-landing（纯展示，表单走第三方或 Pages Functions）
```

Web 三档拿不准时往简单的选：T1 升 T2、T2 升 T3 都只是加目录，不用推翻前端。

## 通用规则（所有预设共用）

- 平台是第一约束：wizard.json 的 `primary` 决定走哪条分支，别给移动 App 套 Web 模板、也别给 Web 站点搭 Xcode 工程。多平台项目按 `primary` 定主栈，次平台在 template-choice.md 里写清是否本期交付。
- Phase 5 产物是唯一事实来源：数据设计以 artifacts/phase-5/ 为准（Web 是 schema.sql，iOS 是从同一批实体推导的 `@Model`，见 P-iOS 小节）；接口/契约以 artifacts/phase-5/ 下产物为准，端点/方法一条不多、一条不少。
- 目录树是合同：Phase 6 scaffold 按所选预设的树建骨架，不加树之外的目录；测试与部署/上架脚本按各预设小节写。
- 落地页 / 营销页本体用 design-taste-frontend 设计实现；产品 UI（T3 的 admin、dashboard、表单页、iOS App 界面）用 frontend-design 或 ui-ux-pro-max（design-taste-frontend 自身声明产品 UI out of scope）。
- 选定预设后立即写 artifacts/phase-5/template-choice.md（平台是哪个、走了决策树哪条分支、选了哪个预设、若换栈/换库写明理由）并 artifact 登记。

---

## Web 预设（primary = PC / H5）

下面 T1/T2/T3 是 Web 产品的三档好默认，按数据需求选。前端本体的设计质量底线（移动端导航、SEO/社交 meta、a11y、无占位死链）见 phase-6 的"落地页交付质量底线"，三档共用。

### T1 static-landing

**适用**：纯展示型落地页——产品介绍、定价、FAQ，最多收一个邮箱。没有需要查询的数据。

**推荐栈**：HTML + CSS + vanilla JS，零框架、零构建步骤。
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

**与 Phase 5 的衔接（T1 的 skipped 口径，以此处为准）**：T1 无数据库——er-diagram 与 schema-ddl 两步标 skipped（逐字执行）：
```
python3 "$SKILL_DIR/scripts/pf_state.py" step 5 er-diagram --status skipped
python3 "$SKILL_DIR/scripts/pf_state.py" step 5 schema-ddl --status skipped
```
api-contract：表单走第三方（Formspree 等）或纯展示无自有端点 → 也标 skipped；只有一个 Pages Function 表单端点（functions/api/subscribe.js）→ api-contract 不 skip，只写它这一个端点。

**Phase 7 部署**：用 deploy-cf-pages skill；命令核心是 `npx wrangler pages deploy public`。

**不做什么**：不引 React/Vue/Tailwind，不加打包器和 npm 依赖，不做 SPA 路由，不写独立后端服务，不为"未来可能的功能"留空壳目录。

### T2 landing-worker

**适用**：落地页 + 轻量数据写入——waitlist、订阅、访问统计、简单留言。有数据但没有人要登录后台看复杂报表。

**推荐栈**：静态前端 + Cloudflare Worker（vanilla fetch handler）+ D1。
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

### T3 landing-fullstack

**适用**：需要 admin 后台（看报名名单、导出数据、改内容）、需要登录，或用户明确要部署在自有服务器上。

**推荐栈**：Node.js 20 + Express + better-sqlite3 + 静态前端，测试用内置 node:test。
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

## 原生 App 预设（primary = APP）

移动 App 不是 Web 站点——它有自己的工程文件、数据持久化方式、测试器和上架渠道。本期实现 **iOS**；Android 留口子（见文末）。

### P-iOS（SwiftUI + SwiftData，本期实现）

**适用**：iOS 17+ 原生移动 App，本地持久化、无需自有后端的产品（习惯打卡、记账、清单、本地工具类）。需要云端账号/同步的复杂后端不在本期预设内——遇到时在 template-choice.md 写明并与用户确认范围。

**推荐栈**：SwiftUI（界面）+ SwiftData（本地持久化，iOS 17+），依赖用 **SPM**（Swift Package Manager）。
理由：SwiftData 是 Apple 一方持久化框架，`@Model` 类直接当模型层用，省掉手写 SQL/DDL 和迁移样板；SwiftUI 声明式 UI 与之同生态、无桥接成本；SPM 是 Xcode 内置依赖管理，不引 CocoaPods 这类外部工具链。纯本地存储的 App **无后端、无 API 契约**——不为想象中的"将来要联网"提前架服务端。

```
MyApp/
├── .productflow/                 # 状态与产物（协议目录，勿手改 state.json）
├── MyApp.xcodeproj/              # Xcode 工程（或 MyApp.xcworkspace，若用 SPM 本地包）
├── MyApp/
│   ├── MyAppApp.swift            # @main App 入口，挂载 .modelContainer(for:)
│   ├── Models/                   # SwiftData @Model 类（数据层，来自 Phase 5 实体）
│   │   └── Item.swift
│   ├── Views/                    # SwiftUI 视图，按屏/功能拆文件
│   │   ├── ContentView.swift
│   │   └── ...
│   ├── ViewModels/               # 可选：@Observable 视图模型（界面状态复杂时才拆）
│   ├── Services/                 # 可选：本地服务抽象（用 protocol，便于测试替身）
│   └── Assets.xcassets/          # 图标、配图、AppIcon
├── MyAppTests/                   # XCTest 单元测试（含 SwiftData 持久化往返）
├── MyAppUITests/                 # XCUITest UI 旅程测试
└── README.md
```

无 CocoaPods 时无 `Podfile`/`Pods/`；SPM 依赖记录在 Xcode 工程的 `Package.resolved` 内。产品代码在工程目录，`.productflow/` 仍只放过程产物（截图、报告、状态），不进 Xcode 工程的编译目标。

**与 Phase 5 的衔接（数据层是 `@Model`，不是 SQL/DDL）**：
- Phase 5 的 module-list / er-diagram 照常做——产出模块清单与实体关系（实体、字段、关系）。
- schema-ddl 步骤**不出 SQLite DDL**，改为从同一批实体推导 SwiftData `@Model` 类：每个实体一个 `@Model class`，字段映射到 Swift 属性，关系用 `@Relationship`，唯一性等约束在模型/写入逻辑里保证（SwiftData 无 SQL 层 UNIQUE，去重在 ModelContext 写入前查重）。把推导出的 `@Model` 写进 `artifacts/phase-5/models.swift`（或并入 er.md），作为 Phase 6 数据层的唯一来源。SQLite-only 的 schema-ddl step 逐字标 skipped：
  ```
  python3 "$SKILL_DIR/scripts/pf_state.py" step 5 schema-ddl --status skipped
  ```
- api-contract：纯本地 App **无网络 API**，api-contract step 标 skipped；若产品需要本地服务抽象（如导出、通知调度），用 `Services/` 下的 Swift `protocol` 定义边界，写进 artifacts/phase-5/，不是 HTTP 端点。
  ```
  python3 "$SKILL_DIR/scripts/pf_state.py" step 5 api-contract --status skipped
  ```

**与 Phase 6 的衔接（实现 + 测试映射到 iOS）**：
- 前置检测（缺了提示用户装 Xcode / 命令行工具，别硬跑报 command not found）：`xcodebuild -version`、`xcrun simctl list devices`，可选 `command -v fastlane`。
- 界面用 SwiftUI 按 direction.md 落地；数据层用 SwiftData，写入前查重保证唯一性。
- 测试器是 **iOS Simulator**，命令是 `xcodebuild test`（指定 `-scheme` + `-destination 'platform=iOS Simulator,name=...'`）；模拟器开关/重置用 `xcrun simctl`，截图用 `xcrun simctl io booted screenshot artifacts/phase-6/preview.png`（替代 Web 的 Playwright 截图）。
- **test-report 四类映射到 iOS**（phase-6 的四类门禁，逐一表态、不允许静默跳过）：
  ① **单元 = XCTest**——模型逻辑、视图模型、纯函数。
  ② **集成 = 数据层 / SwiftData 持久化往返**——在 XCTest 里建临时 `ModelContainer`，「写一条 → 重建 context → 读回」确认真落盘（对应 Web 项目"写入→重启→读回"的持久化验证，凡有持久化必做）。
  ③ **E2E = XCUITest 旅程**——core-analysis.mm.md 的傻瓜式路径在 Simulator 上点通（新建→保存→重开 App 仍在→编辑→删除等）。
  ④ **回归 = 修过的 bug 加 XCUITest 锁**——每个修过的 bug 补一条 XCUITest（注释写明历史事故），跑完即弃的临时脚本不算。

**与 Phase 7 的衔接（构建 + 上架到 TestFlight，停在提审前）**：
- 凭证：Apple Developer 账号 + App Store Connect API key（`.p8` 文件 + key id + issuer id），走 env / 现有部署凭证机制注入（同 Web 的 `~/.productflow/secrets/<项目id>.env`，本阶段已作为环境变量注入，直接引用）。**绝不入库、不打印进 agent-log / 产物 / 留言**。distribution 证书与 provisioning profile 同理由凭证机制提供。
- 构建：`xcodebuild archive` 出 `.xcarchive` → 用 distribution 证书 + provisioning profile `xcodebuild -exportArchive`（或 fastlane `gym`）导出 `.ipa`。
- 上传 **TestFlight**：fastlane `pilot`，或 `xcrun altool` / `notarytool` / Transporter 上传到 App Store Connect 的 TestFlight。
- **停在 TestFlight**：App Review 正式提审那步留用户手动。在交接报告里写清需用户手动做的事——App Store Connect 建 App 记录、注册 Bundle ID、填元数据 / 上传截图（可用 `appstore_shots.py` 抓的竞品截图做版式参考）/ 隐私清单（App Privacy）后再点提交审核。
- 前置检测同 Phase 6（`xcodebuild -version`、`xcrun simctl`，可选 `fastlane`），缺了提示装 Xcode / 命令行工具，别硬跑。

**不做什么**：不引 CocoaPods/Carthage（SPM 够了），不上 UIKit/Storyboard（SwiftUI 全声明式），不为纯本地 App 提前架后端 / 写网络层，不上第三方持久化（Realm/GRDB——SwiftData 即可），本期不替用户点"提交审核"。

### Android（本期 TODO）

primary = APP 且目标含 Android 时：本期预设只实现 iOS。向用户说明——要么本期先交付 iOS（Android 列入后续），要么改做 H5（一套 Web 覆盖双端）。在 template-choice.md 记下这个决定，别默默只做一半。

---

## 偏离协议

预设是默认，不是枷锁。产品确实需要时换栈/换库都行——它本就是"按平台/类型选合适技术"的一部分：

1. 在 artifacts/phase-5/template-choice.md 写明：平台与所选预设、改动了哪一项（换了什么库/框架/形态）、为什么默认预设不满足这个产品；
2. 改动尽量小范围——只替换真正冲突的那一项，目录结构与其余选型仍按最近的预设走，别顺手重写无关部分；
3. 偏离涉及成本或方向（指名某框架、要联网后端、要 WebSocket、要 Android、要复杂云同步）时，在 CLI 向用户明示并得到确认，再进 Phase 6。

## 检查点

- Phase 5 选型完成时（逐字执行；模板名按实际所选替换）：
```
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 5 artifacts/phase-5/template-choice.md --title "技术栈选择与理由"
python3 "$SKILL_DIR/scripts/pf_state.py" step 5 pick-template --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "平台 <PC/H5/APP>，选定预设 <T1/T2/T3/P-iOS>（按实际替换）"
```
- Phase 6 scaffold 完成时：目录树与本文件该预设一致、数据层就位（Web 是 schema.sql 复制进项目并能建表；iOS 是 `@Model` 类 + `.modelContainer` 挂载、能跑空 App），然后
  `python3 "$SKILL_DIR/scripts/pf_state.py" step 6 scaffold --status done`。
- Phase 7 开始时：发布路径由所选预设决定（Web → CF Pages/Worker/单机；iOS → archive/export/上传 TestFlight），不再询问用户选哪条；确认后
  `python3 "$SKILL_DIR/scripts/pf_state.py" step 7 pick-target --status done`。
- 每阶段收尾前照例先跑 `python3 "$SKILL_DIR/scripts/pf_state.py" inbox` 读网页端消息，并逐条 `python3 "$SKILL_DIR/scripts/pf_state.py" reply "<回应>"` 后再继续。
