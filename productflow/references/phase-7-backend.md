# Phase 7：后端实现

何时读本文件：Phase 6（前端实现）已 done、进入后端阶段时。本阶段实现后端（接口 + 数据）并做**后端单元测试**（各模块 / 端点逻辑，fake 适配器 / 内存库 OK，快、隔离）+ 接口文档。前端实现见 `phase-6-frontend.md`；**集成 / E2E 端到端旅程 / 回归等真实拼装后产物的完整验证在 ⑧ 测试阶段做**（见 `phase-8-test.md`）。下一阶段是 ⑧ 测试。

> **无后端项目**（DEC-5 判无后端：纯静态 / 纯前端、原生本地 App）：本阶段整体跳过（操作台隐藏 ⑦）；**功能测试（前端集成 / E2E / 回归）在 ⑧ 测试阶段做**（见 `phase-8-test.md`）。
> 下面的脚手架 / 后端实现 / 调试 / ultracode / 本地预览等**通用实现纪律**，⑥ 前端实现、⑧ 测试阶段同样适用、见 `phase-6-frontend.md` 对应章节。

## 输入（开工前确认齐全）

- `artifacts/phase-5/template-choice.md` —— 选定的预设（含平台与栈），决定本阶段走 Web、iOS、Android 还是 Desktop 分支
- templates.md —— 各预设的目录结构基准与各阶段衔接

平台相关产物（按 template-choice.md 的预设取其一）：

- **Web 预设（primary = PC / H5，T1/T2/T3）**：`artifacts/phase-5/schema.sql`（建库 DDL，T1 纯静态则 skipped）+ `artifacts/phase-5/api.md`（接口契约）。
- **iOS 预设（primary = APP，P-iOS）**：`artifacts/phase-5/models.swift`（从同批实体推导的 SwiftData `@Model` 数据层，替代 schema.sql）；纯本地 App 无网络 API，schema-ddl 与 api-contract 两步已在 Phase 5 标 skipped，本阶段无 api.md。
- **Android 预设（primary = APP，P-Android）**：`artifacts/phase-5/entities.kt`（Room `@Entity`/`@Dao` 数据层，替代 schema.sql）；纯本地 App 无网络 API，schema-ddl 与 api-contract 两步已在 Phase 5 标 skipped，本阶段无 api.md。
- **Desktop 预设（primary = PC，P-Desktop）**：`artifacts/phase-5/schema.sql`（建库 DDL，**和 Web 一样有 SQL 层**，嵌入式 SQLite，Tauri `tauri-plugin-sql`/rusqlite；Electron better-sqlite3）；纯本地桌面 App 无网络 API，api-contract 步骤已在 Phase 5 标 skipped，本阶段无 api.md。

任一该有的缺失，回到对应阶段补齐再开工，不要凭记忆脑补设计、数据层或接口。

**先认清平台分支**：读 template-choice.md 里登记的平台与预设——`PC/H5` 走下文 Web 流程（Node）；`APP` 按预设再分：`P-iOS` 走各步里标注的 **iOS 分支**（Xcode/SwiftUI/SwiftData，后端单元测试用 XCTest），`P-Android` 走各步里标注的 **Android 分支**（Gradle/Kotlin/Jetpack Compose/Room，后端单元测试用 JUnit `./gradlew test`）；`PC` 预设为 `P-Desktop` 时走各步里标注的 **Desktop 分支**（Tauri/Rust + 复用 ④ Web 前端，备选 Electron；SQLite 嵌入式数据层；后端单元测试用前端 Vitest/Jest + Rust `cargo test`）。**XCUITest / Espresso·Compose UI Test / `tauri-driver` 等端到端旅程测试在 ⑧ 测试阶段跑**（见 `phase-8-test.md`）。下面每个 step 先给 Web 主线，再给 iOS 分支，再给 Android 分支，最后给 Desktop 分支，不要混用工具链。

阶段开始：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 7 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 7 后端实现开始"
```

> **共享实现纪律见 ⑥**：本阶段与 ⑥ 前端实现、⑧ 测试共用一套实现纪律——**调试期沟通与开调试现场（边调边读 inbox、`choice ask`+`wait` 暂停问、把运行产物实时开给用户看）**、**ultracode 实现模式（多代理并行 + 对抗式验证）** 两节均见 `phase-6-frontend.md` 对应章节，本文件不重复；verification-before-completion（真跑过才登记）/ systematic-debugging（先复现再修）同样适用，**后端单元测试遵循 TDD**（关键后端逻辑先写测试再实现）。下面直接进入后端专属的系统流程编排与 backend / unit-test / api-docs 三步。

## 系统流程编排 —— 系统流程图 + 模块状态 + 两级评审（涉及后端项目）

> **DEC-5 前置**：纯静态落地页 **T1** / 原生本地无 HTTP 后端（P-iOS、P-Android、纯本地 P-Desktop）= **无后端**——本节整体跳过，只 `log` 一句「本项目无后端，跳过系统流程编排」，照常走下面的 step。**有后端**（T2/T3、带云后端的桌面等）才做这套。它**不推翻** ⑥ 共用的 ultracode 并行（见 `phase-6-frontend.md`），是在其上补「后端流程可视化 + 契约就绪软门 + 模块状态 + 两级评审」，落地需求文档的 PRIN-1/2/3。

**⓪ 系统流程图已由 ⑤ 生成 —— ⑥⑦ 开发时只维护状态、不重新生成**：`.productflow/backend-flow.json`（节点=模块/接口/数据表 + 页面↔模块关联）是 ⑤『功能与数据设计』**做本阶段时顺手产出的产物**（见 phase-5-spec 的「生成系统流程图」节），**不是 ⑥⑦ 才建、也没有单独的"生成"动作**。⑥⑦ 开发时只在这张已有图上**随开发进度更新各模块 / 链路状态**（模块 + 每条链路的接口都随进度更新——页面视图据此给节点上色，并显示每页「接口 X/N 完成」执行进度）：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow set-status --id module:<模块> --status doing   # 模块：todo→doing→done/needfix
python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow set-status --id "api:<接口>" --status done      # 单条链路(接口)做完→done，页面视图即显进度
```

操作台「系统流程图」卡片**在 ⑤ 面板显示**（⑥⑦ 开发页面不再重复渲染，避免和 ⑤ 冗余）：**页面视图**（点页面下钻它的接口+数据）/ **接口·数据全览**。⑥⑦ 开发时**照常用 `backend-flow set-status` 更新节点/链路状态**——节点按状态上色、逐条链路显执行进度，在 ⑤ 的那张图上就能看到。**若 ⑤ 没生成**（老项目 / 被跳过）：回 ⑤ 补做即生成，⑥⑦ 不兜底重造。

**⑴ 契约就绪软门（fan-out 前 · PRIN-3）**：并行开工前，先亮出流程图 + 各模块接口契约，**等用户 go（在流程页圈选 / 留言确认）或短超时**（全自动模式直接过）。契约是单一事实来源，锚稳了再并行，避免设计/契约错误引发大返工。

**全并行开发 + 模块状态**（复用 ⑥ 的 ultracode 并行，**不串行门控**）：**前端已在 ⑥ 前端实现阶段做完**——本阶段各模块**后端并行、按 ⑤ 契约实现并对接 ⑥ 建好的前端**（像 ⑥ 里前端多页面并行那样、这里多模块后端并行）；开工即标进行中、逐个做完标 done——**重做本阶段时操作台已把模块重置为「待做」，哪怕你只是复核式确认（代码已实现、测试已过），也要把涉及的模块逐个 `set-status doing`→`done` 在图上走一遍，别只闷头验证不更新图**（否则成品预览停在「待做」；阶段收尾 server 有兜底补 done，但过程逐个更新体验才好）。状态实时喂开发面板「模块进度清单」+ 流程图节点配色：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow set-status --id module:<模块> --status doing   # todo→doing→done/needfix
```

**两级自动评审（独立 agent 复核，非阻塞）**：
- **① 模块级**（每模块跑通后）：独立 agent 复核该模块 **代码 + 测试 + 契约一致性**——过 → `set-status --status done`；不过 → `set-status --status needfix` 并回修（即 ⑥ ultracode「对抗式验证」落到每个模块 + 写回状态）。
- **② 整体流程评审**（全部模块 done、集成时）：独立 agent 审**整个前后端流程 + 连接闭环**——所有页面/前端流程 + 所有后端接口流程 + 页面↔接口↔数据的连接、有无孤儿 / 契约不一致 / 数据不通，以**系统流程图 + 页面地图 + ER** 为面。

**流程页随时交互改（无固定人工闸 · PRIN-3）**：用户可随时在 ⑥ 描述 / 圈选怎么改（现走 inbox 留言 + preview-feedback） → 你据此改后端设计（`backend-flow.json`）或代码，开发前 / 中 / 后都行；**若动了接口契约 → 触发契约变更传播**（同步改所有依赖该接口的前后端 + 相关测试）。全自动模式则直接按你的设计推进、不等确认。

> **系统流程图上「点节点发意见」的处理**：inbox 里形如 `系统流程图·节点「X」要改：…` 的留言，是用户在系统流程图上点某节点发来的——**该节点操作台已自动标「处理中」脉冲**。你处理这条时：改完该节点后 `backend-flow proc --id <节点id> --state off` 清除脉冲、并 `backend-flow set-status --id <节点id> --status done/needfix` 更新状态（操作台轮询到即实时恢复）；`reply` 回一句改了什么。**别把节点一直挂在「处理中」**。

**收尾·设计方案文档（REQ-8）**：有后端项目在项目目录额外产出 `docs/design.md`（**设计方案**：从 backend-flow 流程图 + ER 导出——模块划分、模块↔接口↔数据表关系、关键数据流），与 `README`（开发 / 使用说明）、`docs/api.md`（接口文档）一起构成项目目录标准文档集，随产品仓库 git。

## Step 1: backend —— 后端 / 数据层实现

**Web 分支（T2/T3 有后端；T1 纯静态本步可标 skipped 或仅实现表单 Function）**：

1. 用 schema.sql 建库（SQLite 系：T2 为 D1、T3 为 better-sqlite3，以 template-choice.md 为准），不要在建库时顺手改表结构；发现 DDL 有问题，先更新 Phase 5 的 schema.sql 再执行，保持单一事实来源。
2. 按 api.md 逐个实现端点。实现与契约出现偏差时，以实际实现为准并在 Step 3 同步回文档。
3. 表单端点必须有**服务端校验**（必填、格式、长度），不能只靠前端。
4. 基础防滥用：honeypot 隐藏字段 **或** 简单频率限制，二选一即可。落地页表单不上验证码、不接风控服务——不过度设计。

**第三方服务对接 —— 真适配器必须写完整，别用 dev 占位蒙混过「完成」**：模块用到第三方服务（短信 / 支付 / OAuth / 地图 / 对象存储…）时，**按官方 API 把真实适配器写完整**（签名、请求、回调验签、错误处理），dev / fake 适配器只作「无 key 时的本地降级 + 单测替身」，**不是**用来替代真实对接的。判据：把真实 key 填进去、切到真 provider，代码就该能真跑（真发短信、真下单），**不留 TODO**。
- **没有真实 key / 沙箱也照样能写完**真适配器（按官方文档写签名与请求，只是没 key 测不了）——「没 key」不是留 TODO 的借口。反例警示：同一项目里短信 `aliyun` 适配器写全了、支付 `wechat` 却只留 dev（`createPaymentService` 永远 return dev），这就是**该写没写的假对接**，不允许。
- 确实要 MVP 阶段先跳过某个真实对接的，**必须显式标占位 + 告知用户**，不许默默 TODO 蒙混成「完成」：
  ```bash
  python3 "$SKILL_DIR/scripts/pf_state.py" backend-flow set-stub --id module:billing --note "微信支付真实对接未实现（当前 dev 占位），接入商户号后补 wechat 适配器"
  ```
  成品预览会把该模块红字标「⚠ 占位 · 真实对接未完成」，收尾时在 CLI 明确告诉用户「X 模块是占位、真实对接待补」——让「没做完」可见，而不是绿色「完成」骗过去。真实对接补齐后 `set-stub --id ... --clear` 清除。

**真 key 不通时的降级要「环境感知」——开发回退 dev、生产报错**：真适配器（aliyun / wechat 等）运行时调用失败（key 错 / 网络不通 / 鉴权失败）时，别一律 throw、也别一律静默回退，按环境分：
- **开发**（`NODE_ENV !== 'production'`）→ catch 住、回退 dev 适配器（继续开发不崩），并打日志「真 key 不通（<错误>），已回退 dev」，让开发者知道 key 有问题、但不阻塞；
- **生产**（`NODE_ENV === 'production'`）→ **原样 throw、绝不回退 dev**——生产静默用 dev 假装成功 = 「以为发了短信 / 收了款」其实没有，是事故。

写法：真 provider 分支返回的对象，每个方法 try 真适配器、catch 后按上面分环境处理；dev 适配器保留（既做「无 key 降级」、又做「开发期真 key 不通的回退」）。

**provider 判据是「有真 key 就真发」——别让 dev 启动命令写死的强制回显盖过用户的 key**：选 provider 的优先级应是「显式指定 > 有真 key 就真发 > 没 key 才回显/dev」。给 dev 加个 `X_DEV_ECHO=1` 强制回显开关（联调不误发真短信/邮件）本身没错，但**别把它写进 `npm run dev` 默认命令、也别让它优先级压过「有没有 key」**——否则用户在操作台填了 key、本地预览却还回显假验证码（「配了 key 怎么没用？」）。正确做法：`npm run dev` 只留 fake 数据驱动 / seed、**不默认设 `X_DEV_ECHO`**（本地就按「有 key 真发、没 key 回显」走，ProductFlow 已把 secrets 注入 dev server）；`X_DEV_ECHO=1` 只写在 **E2E 的 `playwright.config` webServer** 里（测试要拿回显码、即使有 key 也强制回显，不误发真邮件/短信）。

**key 按需动态登记（开发中真用到才加、别等 ⑤ 一次登全）**：写某模块真适配器、真正需要某第三方 key 时，就地 `product-key add` 登记它——`--desc` 写成「给用户看的富文本说明」：**为什么需要、去哪个后台申请、什么格式、关键步骤**（多行写清，操作台会渲染多行）。让用户看到的是「现在要接微信支付、需要商户号 mchid（商户平台 → 账户中心 → API 安全 里拿）」而非干巴巴一个变量名。开发中需要哪个就加哪个、随进展变化；已填的模块继续真实对接、缺的按上文「缺 key 判失败 / 占位」处理。

**iOS 分支（P-iOS，数据层 = SwiftData，无网络后端）**：iOS 纯本地 App 没有"后端服务"——这一步实现的是**本地数据层**。

1. 按 `artifacts/phase-5/models.swift` 把每个实体落成 SwiftData `@Model class` 放进 `Models/`，关系用 `@Relationship`；不要临场改实体结构，发现模型有问题先回去更新 Phase 5 的 models.swift 再实现，保持单一事实来源。
2. 数据读写走 `ModelContext`（`insert`/`delete`/`FetchDescriptor` 查询）；视图里用 `@Query` 取数据。
3. **写入前查重保唯一**：SwiftData 没有 SQL 层 UNIQUE 约束，需要唯一的字段（如名称、外部 id）在 `insert` 前用 `FetchDescriptor` + 谓词查重，已存在则更新而非重复插入。
4. 需要本地服务抽象（导出、通知调度等）时用 `Services/` 下的 `protocol` 定义边界，便于测试替身——**不为想象中的"将来联网"写网络层 / 架后端**。

**Android 分支（P-Android，数据层 = Room，无网络后端）**：Android 纯本地 App 没有"后端服务"——这一步实现的是**本地数据层**。

1. 按 `artifacts/phase-5/entities.kt` 把每个实体落成 Room `@Entity` + 对应 `@Dao` 接口，放进 `data/`；建 `@Database` 并在 `Application` 或 Hilt 模块里单例挂载；不要临场改实体结构，发现有问题先回去更新 Phase 5 的 entities.kt 再实现，保持单一事实来源。
2. 数据读写走 `@Dao`（`@Insert`/`@Delete`/`@Query`）；ViewModel 通过 Repository 取数据，Compose UI 用 `collectAsState` 消费 `Flow`。
3. **写入前查重保唯一**：需要唯一的字段（如名称、外部 id）可用 Room `@Index(unique = true)` 在 schema 层保证，或在 DAO 写入前 `@Query` 查重，已存在则更新（`@Insert(onConflict = OnConflictStrategy.REPLACE)`）而非重复插入。
4. 需要本地服务抽象（导出、通知调度等）时用 Repository `interface` 定义边界，便于测试替身——**不为想象中的"将来联网"写网络层 / 架后端**。

**Desktop 分支（P-Desktop，数据层 = SQLite，无网络后端）**：桌面 App 没有"后端服务"——这一步实现的是**嵌入式 SQLite 数据层**，**和 Web 一样有 SQL 层**，不同于 iOS/Android 的 ORM。

1. 跑 `artifacts/phase-5/schema.sql` DDL 建库——Tauri 用 `tauri-plugin-sql`（前端 JS 侧调 `invoke`）或 Rust 侧 `rusqlite`；Electron 用 `better-sqlite3`。不要临场改表结构，发现 DDL 有问题先回去更新 Phase 5 的 schema.sql 再执行，保持单一事实来源。
2. 数据读写走 SQL（`INSERT`/`SELECT`/`UPDATE`/`DELETE`）；Tauri 通过 `#[tauri::command]` 暴露给前端，前端调 `invoke` 取数据。
3. **写入前查重保唯一**：在 SQL 层用 `UNIQUE` 约束或唯一索引保证（如 `CREATE UNIQUE INDEX ...`），或在写入前 `SELECT` 查重；已存在则 `UPDATE` 而非重复 `INSERT`（`INSERT OR REPLACE` / `ON CONFLICT REPLACE` 也可）。
4. 需要本地服务抽象（文件导出、系统通知等）时用 Tauri `command` / Electron `ipcMain` 定义边界，便于测试替身——**不为想象中的"将来联网"写网络层 / 架后端**。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 backend --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "后端端点实现完成，服务端校验与防滥用就位 / iOS 数据层 @Model 就位，写入查重保唯一 / Android 数据层 Room @Entity/@Dao 就位，写入查重保唯一 / Desktop SQLite 数据层就位，schema.sql 已建库，查重保唯一（按平台取其一）"
```

## Step 2: unit-test —— 后端单元测试

本步只做 **单元测试**（`unit-test`）：各后端模块 / 端点逻辑，用 **fake 适配器 / 内存库**隔离，**快、可反复跑**。**集成 / E2E 端到端旅程 / 回归 / 数据持久化往返 / test-report 门禁等真实拼装后产物的完整验证在 ⑧ 测试阶段做**（见 `phase-8-test.md`）——本步不碰。遵循 TDD：关键后端逻辑先写测试（红）再实现（绿）。Web 主线见下；**iOS 分支见本步末尾的"iOS 单元测试分支"**（XCTest）；**Android 分支见"Android 单元测试分支"**（JUnit `./gradlew test`）；**Desktop 分支见"Desktop 单元测试分支"**（前端 Vitest/Jest + Rust `cargo test`）。（用 ultracode 时，让独立 agent 复核代码并把单元测试并行做厚，对抗式确认而非自说自话——见 ⑥「ultracode 实现模式」。）调试这层往往是长循环：**按 ⑥「调试期沟通与开调试现场」边调边读 `inbox`、卡在歧义点用 `choice ask`+`wait` 暂停问、并把在跑的产物实时开给用户看**，别把沟通攒到阶段收尾。

- **API 单元测试**：每个端点至少覆盖成功路径 + 一个校验失败路径（如必填缺失返回 4xx）。用 fake 适配器 / 内存库跑，快而隔离；真实拼装后的端到端旅程、数据持久化往返留给 ⑧。
- **落成项目内可复跑文件**：单元测试写成项目内固定可复跑的测试文件（Web `tests/unit/` 或框架约定目录），**临时脚本不算测试**——它跑完即弃、下个 bug 照漏。动笔前先确认真实的函数签名 / 端点路由 / 元素标识（Web `grep` DOM 的 id/role 或路由），别凭记忆猜（猜错就是假失败）。

把单元测试命令写进项目根目录 README（Web 如 `npm test`；iOS 如 `xcodebuild test -scheme MyApp -destination '...'`（XCTest target）；Android 如 `./gradlew test`；Desktop 如 `cargo test`、`npm run test`（前端）），让任何人不读代码就能复跑。集成 / E2E 命令由 ⑧ 补进 README。

### iOS 单元测试分支（P-iOS）

iOS 单元测试器是 **XCTest**（`xcodebuild test` 指定 `-scheme` + XCTest target；本步不跑 XCUITest UI 自动化——那在 ⑧）。**前置检测** `xcodebuild -version`，缺了提示装 Xcode，别硬跑。落成项目内 `MyAppTests/`（XCTest）可复跑文件——**临时脚本不算测试**。

- **①单元 = XCTest**：模型逻辑、`@Observable` 视图模型、纯函数。每类逻辑至少一条成功路径 + 一条边界/失败路径（如写入查重命中时不重复插入）。**SwiftData 持久化往返、XCUITest 旅程、回归锁属于 ⑧**（见 `phase-8-test.md`）。

### Android 单元测试分支（P-Android）

Android 单元测试是 `./gradlew test`（JUnit，本机 JVM 跑，不需 Emulator；仪器测试 / Compose UI Test 旅程在 ⑧）。**前置检测** `./gradlew --version`，缺了提示装 Android Studio / SDK，别硬跑。落成项目内 `app/src/test/` 可复跑文件——**临时脚本不算测试**。

- **①单元 = JUnit**：ViewModel 逻辑、纯函数、Repository 逻辑（用 fake DAO 替身）。每类逻辑至少一条成功路径 + 一条边界/失败路径（如写入查重命中时不重复插入）。**Room 持久化往返、Compose UI Test / Espresso 旅程、回归锁属于 ⑧**（见 `phase-8-test.md`）。

### Desktop 单元测试分支（P-Desktop）

Desktop 单元测试 = 前端逻辑（Vitest/Jest）+ Rust `cargo test`（SQLite 持久化往返、`tauri-driver`/Playwright E2E 旅程在 ⑧）。**前置检测** `rustc --version`、`cargo --version`，缺了提示装 Rust，别硬跑。落成项目内可复跑文件（前端 `tests/`；Rust `src-tauri/tests/` 或 `#[cfg(test)]`）——**临时脚本不算测试**。

- **①单元 = 前端 Vitest/Jest + Rust `cargo test`**：前端业务逻辑（表单校验、数据处理纯函数）用 Vitest/Jest 覆盖；Rust `#[tauri::command]` 核心逻辑用 `cargo test` 覆盖。每类逻辑至少一条成功路径 + 一条边界/失败路径（如写入查重命中时不重复插入）。**SQLite 持久化往返、桌面 E2E 旅程、回归锁属于 ⑧**（见 `phase-8-test.md`）。

**配了真 key 就顺带验一下 key 对不对（没配则保持 dev、不验、不阻塞单测）**：单元测试主体仍用 fake 适配器 / 内存库（快、隔离，没 key 也全绿）。但**若用户已在操作台填了某第三方 key**（secrets 里有值），就多加一条「真 key 连通性检查」——切真 provider、对第三方做一次最小真实调用，确认 key 真能用。**注意选对接口**：只验 AccessKey/签名用查询类（如短信 `QuerySendDetails`，不费钱、幂等）；但**要连模板 + 签名一起验，得用真发接口（如 `SendSms`）**——模板 code 错（`isv.SMS_TEMPLATE_ILLEGAL`）只有真发路径才暴露、查询类抓不到（模板非法时阿里云在下发前就拒、不会真发出短信，所以拿真发去验模板也安全）。发到测试号（如 13800138000）：
- key 对 → 通过；
- **key 错**（AccessKey / 签名 / 模板任一错）→ `backend-flow set-status --id module:X --status needfix --note "具体哪个错 + 阿里云错误码，如「SMS 模板 code 不对（isv.SMS_TEMPLATE_ILLEGAL），请在操作台重填 SMS_TEMPLATE_CODE」"`——**`--note` 把原因存进节点，用户点该模块就在弹窗看到「为什么标红」**（别只 `log`、点开看不到）。**别等到 ⑧ 才发现填错了**。

后端单元测试全绿后（本阶段只有 `unit-test` 一个测试步；集成 / E2E / 回归 + test-report 四类门禁在 ⑧ 测试阶段统一做与审计，见 `phase-8-test.md`）：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 unit-test --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "后端单元测试全绿（各模块/端点逻辑覆盖成功 + 校验失败路径），集成/E2E/回归在 ⑧ 测试阶段"
```

单元测试不过不许进入下一步——这是 verification-before-completion 的硬约束。四类测试（含本步单元）的完整表态由 ⑧ 的 `test-report` 门禁统一审计（流水线不靠 agent 一句口头"测过了"放行）。

## Step 3: api-docs —— 文档

**Web 分支（有网络 API）**：

1. **`docs/api.md`**（项目根目录下）：按**实际实现**同步 Phase 5 的 api.md——端点、参数、状态码、错误格式，每个端点附一条可直接执行的 curl 示例。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤、（单元）测试命令、部署入口（指向 Phase 9，写"见 .productflow 流水线 Phase 9"即可，不展开）。
3. 把 docs/api.md 复制为过程产物并登记，操作台展示接口文档：

```bash
cp docs/api.md .productflow/artifacts/phase-7/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/api-docs.md --title "API 接口文档"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 api-docs --status done
```

**iOS 分支（P-iOS，无网络 API）**：纯本地 App 没有 HTTP 端点，本步改为给**数据层 + 本地服务**留文档：

1. **`docs/data-model.md`**（项目根目录下）：列出实际落地的 SwiftData `@Model` 类——每个实体的字段、关系（`@Relationship`）、唯一性约束在哪段写入逻辑里保证；若有 `Services/` 下的 `protocol`，写清各方法的输入/输出/副作用（替代 curl 示例）。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤（Xcode 打开、选 scheme/Simulator 跑）、（单元）测试命令（`xcodebuild test ...`）、上架入口（指向 Phase 9，写"见 .productflow 流水线 Phase 9（archive → TestFlight）"即可，不展开）。
3. 把 docs/data-model.md 复制为过程产物并登记，操作台展示数据层文档（artifact 标题用"数据模型文档"以区分 Web 的接口文档）：

```bash
cp docs/data-model.md .productflow/artifacts/phase-7/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/api-docs.md --title "数据模型文档（SwiftData @Model）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 api-docs --status done
```

（产物文件名仍用 `api-docs.md` 以与现有 step/检查点登记一致；iOS 项目里它装的是数据模型文档。）

**Android 分支（P-Android，无网络 API）**：纯本地 App 没有 HTTP 端点，本步改为给**数据层 + 本地服务**留文档：

1. **`docs/data-model.md`**（项目根目录下）：列出实际落地的 Room `@Entity` 与 `@Dao`——每个实体的字段、关系（外键/联结表）、`@Index(unique = true)` 或写入查重逻辑在哪里保证；若有 Repository `interface`，写清各方法的输入/输出/副作用（替代 curl 示例）；有 schema 迁移（`Migration`）时列出版本与变更。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤（Android Studio 打开、选 AVD 跑，或 `./gradlew installDebug` + `adb shell am start`）、测试命令（单元 `./gradlew test`；仪器测试 `./gradlew connectedAndroidTest` 在 ⑧）、上架入口（指向 Phase 9，写"见 .productflow 流水线 Phase 9（AAB 上传 Play Console）"即可，不展开）。
3. 把 docs/data-model.md 复制为过程产物并登记，操作台展示数据层文档（artifact 标题用"数据模型文档"以区分 Web 的接口文档）：

```bash
cp docs/data-model.md .productflow/artifacts/phase-7/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/api-docs.md --title "数据模型文档（Room @Entity/@Dao）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 api-docs --status done
```

（产物文件名仍用 `api-docs.md` 以与现有 step/检查点登记一致；Android 项目里它装的是数据模型文档。）

**Desktop 分支（P-Desktop，无网络 API，数据层 = SQLite）**：桌面 App 没有 HTTP 端点，本步改为给**数据层 + 本地 Tauri command**留文档：

1. **`docs/data-model.md`**（项目根目录下）：列出实际落地的 SQLite 表结构（同 Web 的 schema.sql，但以桌面应用视角描述）——每张表的字段、类型、`UNIQUE` 约束/索引；若有 Tauri `#[tauri::command]` 或 Electron `ipcMain` handler，写清各方法的输入/输出/副作用（替代 curl 示例）。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤（`cargo tauri dev` 或 `npm run start`）、测试命令（单元 `cargo test`、`npm run test`；E2E `npm run test:e2e` 在 ⑧）、打包入口（`cargo tauri build` 生成安装包，指向 Phase 9，写"见 .productflow 流水线 Phase 9（tauri build/安装包）"即可，不展开）。
3. 把 docs/data-model.md 复制为过程产物并登记，操作台展示数据层文档（artifact 标题用"数据模型文档"以区分 Web 的接口文档）：

```bash
cp docs/data-model.md .productflow/artifacts/phase-7/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/api-docs.md --title "数据模型文档（SQLite 表结构）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 api-docs --status done
```

（产物文件名仍用 `api-docs.md` 以与现有 step/检查点登记一致；Desktop 项目里它装的是 SQLite 数据模型文档。）

## 检查点（阶段收尾，顺序执行）

1. 读网页端消息并逐条回应（有改动要求就先处理再收尾）：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" inbox
   python3 "$SKILL_DIR/scripts/pf_state.py" reply "<对该条留言的回应>"   # 每条留言各回一次
   ```

2. 写本阶段汇总 `artifacts/phase-7/build-summary.md`（一页：后端技术栈与目录结构、已实现清单【Web=端点清单 / iOS=`@Model` 数据层清单 / Android=Room `@Entity`/`@Dao` 清单 / Desktop=SQLite 表清单】、后端单元测试结果摘要、文档位置、已知限制），并登记：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/build-summary.md --title "Phase 7 后端实现汇总"
   ```

3. 确认 backend、unit-test、api-docs 三个 step 均为 done、api-docs.md（iOS/Android/Desktop 为数据模型文档）+ build-summary.md 均已登记（有后端项目还应确认 `docs/design.md` 设计方案文档已产出）。**并确认涉第三方服务的模块：真适配器都写完整了、确实要占位的都已 `set-stub` 显式声明——不留「该写没写」的未声明假对接**。**并跑 `python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" scan-keys`**——它扫代码里真引用的第三方 env、对比 product-keys 登记，把「代码用了却没登记」的 `missing` 逐个 `product-key add` 补上（**以代码实际引用的变量名为准、别自己猜名字**）；把 `stale`（登记了、但代码已不再引用）的核对后处理——**功能删了就 `product-key rm --key X` 删掉过时登记**（若是真适配器还没写的占位则留着 + `set-stub`）。**改某模块、去掉某功能时，顺手把它独有的 key 登记一并删掉**——别让 key 列表和代码脱节。根治「漏找用户要 key」+「功能删了 key 没删」。**集成 / E2E / 回归 + test-report 门禁不在本阶段**（在 ⑧，见 `phase-8-test.md`）。**⑦ 不做 impl-check**——那套「④ 每页×平台都有实现截图」的页面覆盖硬闸是 ⑥ 前端阶段的门禁（见 `phase-6-frontend.md`），不属于后端阶段。

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" phase 7 --status done
   python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 7 完成：后端 + 单元测试 + 文档就绪，待用户确认进入 ⑧ 测试"
   ```

4. 在 CLI 向用户汇报：后端单元测试通过情况、文档位置（Web=API 文档 / iOS=数据模型文档 / Android=数据模型文档 / Desktop=SQLite 数据模型文档），请用户在网页或 CLI 确认后进入 ⑧ 测试（集成 + E2E 端到端旅程 + 回归 + test-report 门禁；无后端项目做前端集成 / E2E；见 phase-8-test.md）。用户此前明确说过"全自动"则不停留，直接进入 ⑧ 测试。
