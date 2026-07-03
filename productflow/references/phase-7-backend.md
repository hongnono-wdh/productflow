# Phase 7：后端实现 · 测试

何时读本文件：Phase 6（前端实现）已 done、进入后端阶段时。本阶段实现后端（接口 + 数据）并做 **单元测试 + 集成测试**——**集成测试必须确保功能端到端完整跑通、没问题**，不是走过场。前端实现见 `phase-6-frontend.md`。

> **无后端项目**（DEC-5 判无后端：纯静态 / 纯前端）：本阶段整体跳过（操作台隐藏 ⑦）；**单元测试 + 集成测试并入 ⑥ 前端实现**（见 `phase-6-frontend.md`）。
> 下面的脚手架 / 前后端实现 / 调试 / ultracode / 本地预览等**通用实现纪律**，⑥ 前端实现阶段同样适用、见 `phase-6-frontend.md` 对应章节。

## 输入（开工前确认齐全）

- `artifacts/phase-5/template-choice.md` —— 选定的预设（含平台与栈），决定本阶段走 Web、iOS、Android 还是 Desktop 分支
- templates.md —— 各预设的目录结构基准与各阶段衔接

平台相关产物（按 template-choice.md 的预设取其一）：

- **Web 预设（primary = PC / H5，T1/T2/T3）**：`artifacts/phase-5/schema.sql`（建库 DDL，T1 纯静态则 skipped）+ `artifacts/phase-5/api.md`（接口契约）。
- **iOS 预设（primary = APP，P-iOS）**：`artifacts/phase-5/models.swift`（从同批实体推导的 SwiftData `@Model` 数据层，替代 schema.sql）；纯本地 App 无网络 API，schema-ddl 与 api-contract 两步已在 Phase 5 标 skipped，本阶段无 api.md。
- **Android 预设（primary = APP，P-Android）**：`artifacts/phase-5/entities.kt`（Room `@Entity`/`@Dao` 数据层，替代 schema.sql）；纯本地 App 无网络 API，schema-ddl 与 api-contract 两步已在 Phase 5 标 skipped，本阶段无 api.md。
- **Desktop 预设（primary = PC，P-Desktop）**：`artifacts/phase-5/schema.sql`（建库 DDL，**和 Web 一样有 SQL 层**，嵌入式 SQLite，Tauri `tauri-plugin-sql`/rusqlite；Electron better-sqlite3）；纯本地桌面 App 无网络 API，api-contract 步骤已在 Phase 5 标 skipped，本阶段无 api.md。

任一该有的缺失，回到对应阶段补齐再开工，不要凭记忆脑补设计、数据层或接口。

**先认清平台分支**：读 template-choice.md 里登记的平台与预设——`PC/H5` 走下文 Web 流程（Node/Playwright）；`APP` 按预设再分：`P-iOS` 走各步里标注的 **iOS 分支**（Xcode/SwiftUI/SwiftData，测试用 XCTest/XCUITest 在 Simulator 跑），`P-Android` 走各步里标注的 **Android 分支**（Gradle/Kotlin/Jetpack Compose/Room，测试用 JUnit + Espresso/Compose UI Test 在 Emulator 跑）；`PC` 预设为 `P-Desktop` 时走各步里标注的 **Desktop 分支**（Tauri/Rust + 复用 ④ Web 前端，备选 Electron；SQLite 嵌入式数据层；测试用前端 Vitest/Jest + Rust `cargo test` + `tauri-driver` E2E）。下面每个 step 先给 Web 主线，再给 iOS 分支，再给 Android 分支，最后给 Desktop 分支，不要混用工具链。

阶段开始：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 7 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 7 后端实现开始"
```

> **共享实现纪律见 ⑥**：本阶段与 ⑥ 前端实现共用一套实现纪律——**全阶段纪律（TDD / verification-before-completion / systematic-debugging）**、**调试期沟通与开调试现场（边调边读 inbox、`choice ask`+`wait` 暂停问、把运行产物实时开给用户看）**、**ultracode 实现模式（多代理并行 + 对抗式验证）** 三节均见 `phase-6-frontend.md` 对应章节，本文件不重复；下面直接进入后端专属的系统流程编排与 backend / 测试 / 文档三步。

## 系统流程编排 —— 系统流程图 + 模块状态 + 两级评审（涉及后端项目）

> **DEC-5 前置**：纯静态落地页 **T1** / 原生本地无 HTTP 后端（P-iOS、P-Android、纯本地 P-Desktop）= **无后端**——本节整体跳过，只 `log` 一句「本项目无后端，跳过系统流程编排」，照常走下面的 step。**有后端**（T2/T3、带云后端的桌面等）才做这套。它**不推翻** ⑥ 共用的 ultracode 并行（见 `phase-6-frontend.md`），是在其上补「后端流程可视化 + 契约就绪软门 + 模块状态 + 两级评审」，落地需求文档的 PRIN-1/2/3。

**⓪ 系统流程图已由 ⑤ 生成 —— ⑥⑦ 开发时只维护状态、不重新生成**：`.productflow/backend-flow.json`（节点=模块/接口/数据表 + 页面↔模块关联）是 ⑤『功能与数据设计』**做本阶段时顺手产出的产物**（见 phase-5-spec 的「生成系统流程图」节），**不是 ⑥⑦ 才建、也没有单独的"生成"动作**。⑥⑦ 开发时只在这张已有图上**随开发进度更新各模块 / 链路状态**（模块 + 每条链路的接口都随进度更新——页面视图据此给节点上色，并显示每页「接口 X/N 完成」执行进度）：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow set-status --id module:<模块> --status doing   # 模块：todo→doing→done/needfix
python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow set-status --id "api:<接口>" --status done      # 单条链路(接口)做完→done，页面视图即显进度
```

操作台「系统流程图」卡片**在 ⑤ 面板显示**（⑥⑦ 开发页面不再重复渲染，避免和 ⑤ 冗余）：**页面视图**（点页面下钻它的接口+数据）/ **接口·数据全览**。⑥⑦ 开发时**照常用 `backend-flow set-status` 更新节点/链路状态**——节点按状态上色、逐条链路显执行进度，在 ⑤ 的那张图上就能看到。**若 ⑤ 没生成**（老项目 / 被跳过）：回 ⑤ 补做即生成，⑥⑦ 不兜底重造。

**⑴ 契约就绪软门（fan-out 前 · PRIN-3）**：并行开工前，先亮出流程图 + 各模块接口契约，**等用户 go（在流程页圈选 / 留言确认）或短超时**（全自动模式直接过）。契约是单一事实来源，锚稳了再并行，避免设计/契约错误引发大返工。

**全并行开发 + 模块状态**（复用 ⑥ 的 ultracode 并行，**不串行门控**）：**前端已在 ⑥ 前端实现阶段做完**——本阶段各模块**后端并行、按 ⑤ 契约实现并对接 ⑥ 建好的前端**（像 ⑥ 里前端多页面并行那样、这里多模块后端并行）；开工即标进行中，之后按评审结果更新——状态实时喂开发面板「模块进度清单」+ 流程图节点配色：

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

## Step 2: 测试 —— 单元测试(unit-test) + 集成测试(integration-test)

**对应 ⑦ 的两个步骤**：**单元测试**（`unit-test`，各模块 / 端点逻辑，fake 适配器 / 内存库 OK）+ **集成测试**（`integration-test`，下面的 E2E 用户旅程 + 数据持久化 + 真实产物端到端）——**集成测试必须确保功能端到端完整跑通、没问题**，不是走过场。两层全部真实跑过。Web 主线见下；**iOS 分支见本步末尾的"iOS 测试分支"**（XCTest + XCUITest 在 Simulator 跑）；**Android 分支见本步末尾的"Android 测试分支"**（JUnit + Espresso/Compose UI Test 在 Emulator 跑）；**Desktop 分支见本步末尾的"Desktop 测试分支（P-Desktop）"**（前端 Vitest/Jest + Rust `cargo test` + `tauri-driver`/Playwright E2E），四类测试门禁四条分支共用。（用 ultracode 时，让独立 agent 复核代码并把四类测试分头并行做厚，对抗式确认而非自说自话——见 ⑥「ultracode 实现模式」。）调试这层往往是长循环：**按 ⑥「调试期沟通与开调试现场」边调边读 `inbox`、卡在歧义点用 `choice ask`+`wait` 暂停问、并把在跑的产物实时开给用户看**，别把沟通攒到阶段收尾。

- **API 测试**：每个端点至少覆盖成功路径 + 一个校验失败路径（如必填缺失返回 4xx）。
- **E2E 用户旅程测试**（@playwright/test，落为项目内可复跑的测试文件如 `tests/e2e/journeys.spec.*` + `npm run test:e2e`——**临时截图脚本不算测试**，它跑完就消失，下个 bug 照样漏网）。**非 Node 项目（T1 纯静态没有 npm 工具链，或 iOS 项目）**别因为没 Node 就退回一次性脚本——落成等价的可复跑测试文件：Web 纯静态用 **Python Playwright（`from playwright.sync_api import sync_playwright`，chromium headless）** 写 `tests/e2e/test_journeys.py`（自起本地 HTTP server / BASE_URL 可指向容器）；**iOS 用 XCUITest**（见"iOS 测试分支"）。作用与 @playwright/test 一致：固定、可复跑、跑在真实产物上。旅程清单的来源固定三处：
  1. **auth/会话全循环**：注册 → 进入 → 退出 → 登录 → 再进入（历史教训：只测注册不测"退出再登录"，曾让"退出后停在注册 tab"的 bug 直接漏到用户手上）；
  2. **core-analysis.mm.md 的傻瓜式路径**逐步走通——那是产品对用户的核心承诺，承诺本身必须有测试锁住；
  3. **每个表单/弹窗的失败路径**：错误提示必须"可见"（断言 toBeVisible 而非仅存在——hidden 属性被 CSS display 顶掉是真实发生过的事故）。
  修过的每个 bug 加一条回归锁用例，注释里写明历史事故。

E2E 必须跑在**真实最终产物**上（容器或构建产物，BASE_URL 可配置），不是 dev server——单元测试用 fake 适配器和内存库没问题，但旅程测试的意义就是验证拼装后的真品。共享实例的旅程测试用 `workers: 1` 串行，避免互踩和触发限流。

- **数据持久化验证**（凡有持久化的项目必做）：Web 在真实部署形态上「写一条 → 重启服务/容器 → 读回来」，确认数据真落盘。内存库和单进程生命周期内的测试都测不出持久化问题——历史事故：SQLite 的 **WAL 日志模式在 Docker Desktop(macOS) 的 bind mount 上写入不落盘**（虚拟文件系统不支持 WAL 的共享内存 mmap），注册"成功"但重启即丢、跨连接查不到。修复是 `journal_mode = DELETE`，并加一条「重开连接后数据仍在」的回归测试锁住。选 SQLite + 容器 + bind mount 时尤其要测这一项。**iOS 对应项**：SwiftData 持久化往返（写一条 → 重建 `ModelContext`/`ModelContainer` → 读回），见"iOS 测试分支"的②集成。**Android 对应项**：Room 持久化往返（写一条 → 用 `Room.inMemoryDatabaseBuilder` 测内存库或真实库「写→重建/重启→读回」→ 断言数据仍在），见"Android 测试分支"的②集成。

- **验收纪律**：自查/验收一律跑仓库里的正式测试套件（Web `npm test` + `npm run test:e2e`；iOS `xcodebuild test`；Android `./gradlew test` + `./gradlew connectedAndroidTest`），**不要现场手写一次性脚本来"走一遍看看"**——临时脚本会凭记忆猜元素 id/选择器（猜错就是假失败，浪费来回），且跑完即弃、下个 bug 照漏。要覆盖新交互就扩充正式套件：动笔前先确认真实的元素标识（Web `grep` DOM 的 id/role；iOS 用 `accessibilityIdentifier` 标记控件，XCUITest 按 id 取；Android 用 `Modifier.testTag` 或 `contentDescription`，Compose UI Test 按 tag 取），再写进测试文件。

把测试命令写进项目根目录 README（Web 如 `npm test`、`npm run test:e2e`；iOS 如 `xcodebuild test -scheme MyApp -destination '...'`；Android 如 `./gradlew test`、`./gradlew connectedAndroidTest`；Desktop 如 `cargo test`、`npm run test`（前端）、`npm run test:e2e`（`tauri-driver`/Playwright E2E））），让任何人不读代码就能复跑。

### iOS 测试分支（P-iOS）

iOS 没有 Node/Playwright 工具链，测试器是 **iOS Simulator**，命令是 `xcodebuild test`（指定 `-scheme` + `-destination 'platform=iOS Simulator,name=iPhone 15'` 之类）；模拟器开关/重置用 `xcrun simctl`。**前置检测** `xcodebuild -version`、`xcrun simctl list devices`，缺了提示装 Xcode，别硬跑。所有测试落成项目内 `MyAppTests/`（XCTest）/ `MyAppUITests/`（XCUITest）下可复跑的文件——**临时脚本不算测试**，跟 Web 同纪律。四类门禁映射到 iOS：

- **①单元 = XCTest**：模型逻辑、`@Observable` 视图模型、纯函数。每类逻辑至少一条成功路径 + 一条边界/失败路径（如写入查重命中时不重复插入）。
- **②集成 = SwiftData 持久化往返**（凡有持久化必做，对应 Web 的"写→重启→读回"）：在 XCTest 里建**临时** `ModelContainer`（`isStoredInMemoryOnly: false` 指向临时目录，或新建独立 container），「写一条 → 重建 `ModelContext`/`ModelContainer` → 读回」，断言数据仍在、字段一致、唯一性约束生效。内存里写完直接读不算往返——必须跨 context/container 重建才测得出真落盘。
- **③E2E = XCUITest 旅程**：core-analysis.mm.md 的傻瓜式路径在 Simulator 上点通（新建 → 保存 → **杀掉并重开 App 数据仍在** → 编辑 → 删除等核心循环）。控件用 `accessibilityIdentifier` 标记后按 id 取；断言用 `XCTAssert(element.exists)` / `waitForExistence`，别靠屏幕坐标硬点。旅程清单来源同上文三处（会话/状态全循环、核心承诺路径、每个表单弹窗的失败提示可见）。
- **④回归 = 修过的 bug 加 XCUITest 锁**：每个修过的 bug 补一条 XCUITest（或 XCTest，视 bug 层级），注释写明历史事故；跑完即弃的临时脚本不算。

iOS 端的"E2E 跑在真实最终产物上"= 用 **Release 配置**或与上架一致的构建跑 XCUITest，别只测 Debug。

### Android 测试分支（P-Android）

Android 没有 Node/Playwright/Xcode 工具链，测试器是 **Android Emulator（AVD）**，命令是 `./gradlew test`（单元，JUnit，本机 JVM 跑，不需 Emulator）和 `./gradlew connectedAndroidTest`（仪器测试，需 Emulator/真机）。**前置检测** `./gradlew --version`、`adb --version`、`emulator -list-avds`，缺了提示装 Android Studio / SDK，别硬跑。所有测试落成项目内可复跑文件（`app/src/test/`=单元；`app/src/androidTest/`=仪器测试）——**临时脚本不算测试**，跟 Web/iOS 同纪律。四类门禁映射到 Android：

- **①单元 = JUnit**：ViewModel 逻辑、纯函数、Repository 逻辑（用 fake DAO 替身）。每类逻辑至少一条成功路径 + 一条边界/失败路径（如写入查重命中时不重复插入）。
- **②集成 = Room 持久化往返**（凡有持久化必做，对应 Web 的"写→重启→读回"）：在 JUnit 仪器测试里用 `Room.inMemoryDatabaseBuilder` 建临时库（或真实库写→重建/重启→读回），「写一条 → 重建 Database 实例 → 读回」，断言数据仍在、字段一致、唯一性约束生效。内存库写完直接读不算往返——必须跨实例重建才测得出真落盘。
- **③E2E = Compose UI Test / Espresso 旅程**：core-analysis.mm.md 的傻瓜式路径在 Emulator 上点通（新建 → 保存 → **杀进程重开 App 数据仍在** → 编辑 → 删除等核心循环）。控件用 `Modifier.testTag` 或 `contentDescription` 标记后用 `onNodeWithTag`/`onNodeWithContentDescription` 取；断言用 `assertIsDisplayed()`/`assertExists()`。旅程清单来源同上文三处（会话/状态全循环、核心承诺路径、每个表单弹窗的失败提示可见）。
- **④回归 = 修过的 bug 加 Compose UI Test / JUnit 锁**：每个修过的 bug 补一条测试（视 bug 层级选单元或仪器测试），注释写明历史事故；跑完即弃的临时脚本不算。

Android 端的"E2E 跑在真实最终产物上"= 用 **Release 构建**（`./gradlew assembleRelease` + installRelease）跑 connectedAndroidTest，别只测 Debug。

### Desktop 测试分支（P-Desktop）

Desktop 测试器是前端测试框架（Vitest/Jest）+ Rust 测试（`cargo test`）+ 桌面旅程（`tauri-driver`+WebDriver，或前端 Playwright 跑渲染层）。**前置检测** `rustc --version`、`cargo --version`、`cargo tauri --version`，缺了提示装 Rust/Tauri CLI，别硬跑。所有测试落成项目内可复跑文件（前端 `tests/`；Rust `src-tauri/tests/`）——**临时脚本不算测试**，跟 Web/iOS/Android 同纪律。四类门禁映射到 Desktop：

- **①单元 = 前端逻辑（Vitest/Jest）+ Rust `cargo test`**：前端业务逻辑（表单校验、数据处理纯函数）用 Vitest/Jest 覆盖；Rust `#[tauri::command]` 核心逻辑用 `cargo test` 覆盖。每类逻辑至少一条成功路径 + 一条边界/失败路径（如写入查重命中时不重复插入）。
- **②集成 = 本地 SQLite 持久化往返**（凡有持久化必做，对应 Web 的"写→重启→读回"）：「写一条 → 重启应用 → 读回」，断言数据仍在、字段一致、唯一性约束生效（SQL UNIQUE 索引）。Tauri 可用 Rust 集成测试直接操 `rusqlite`；Electron 用 Jest + `better-sqlite3` 建临时库测往返。内存里写完直接读不算往返——必须跨进程重启才测得出真落盘。
- **③E2E = 桌面应用旅程**：core-analysis.mm.md 的傻瓜式路径在桌面窗口上走通（新建 → 保存 → **重启应用数据仍在** → 编辑 → 删除等核心循环）。优先用 `tauri-driver`+WebDriver（`WebDriver::new`）驱动；无驱动则退化为前端 Playwright 跑渲染层旅程（`cargo tauri dev` 先起，再 Playwright 连 webview DevTools port）。旅程清单来源同上文三处（会话/状态全循环、核心承诺路径、每个表单弹窗的失败提示可见）。
- **④回归 = 修过的 bug 加测试锁**：每个修过的 bug 补一条测试（视 bug 层级选前端单元/Rust 单元/E2E），注释写明历史事故；跑完即弃的临时脚本不算。

Desktop 端的"E2E 跑在真实最终产物上"= 用 **Release 构建**（`cargo tauri build`）跑 E2E，别只测 dev 模式。

**测试小结产物（门禁，必做）**：把这次测试情况写成 `artifacts/phase-7/test-report.md` 并登记——对**四类测试逐一表态**：① 单元 ② 接口集成 ③ 端到端(E2E) ④ 核心功能回归。每类要么「✅ 通过（写清测了什么、几条、复跑命令）」，要么「N/A（一句理由，如 T1 纯静态无后端 → 单元/接口集成 N/A）」。iOS 四类映射：①=XCTest，②=SwiftData 持久化往返，③=XCUITest 旅程，④=XCUITest 回归锁（iOS 项目这四类一般都该有实测，"无网络 API"不等于免测——②落到持久化往返而非接口）。Android 四类映射：①=JUnit（ViewModel/纯逻辑），②=Room 持久化往返，③=Compose UI Test / Espresso 旅程，④=Compose UI Test / JUnit 回归锁（Android 项目这四类一般都该有实测，"无网络 API"不等于免测——②落到 Room 持久化往返而非接口）。Desktop 四类映射：①=前端 Vitest/Jest + Rust `cargo test`，②=SQLite 持久化往返（写→重启→读回），③=`tauri-driver`/Playwright E2E 旅程，④=回归测试锁（Desktop 项目这四类一般都该有实测，"无网络 API"不等于免测——②落到 SQLite 持久化往返而非接口）。**不允许某类既不做、也不声明 N/A**——静默跳过测试是这条流水线最容易漏的坑。这份 test-report 会显示在操作台，是「测试做没做、做到什么程度」**唯一可审计的凭证**（流水线不靠 agent 一句口头"测过了"放行）。

测试全绿、且 test-report 四类都已表态后：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/test-report.md --title "测试小结（单元/集成/E2E/回归）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 unit-test --status done
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 integration-test --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "测试全绿：单元 + 集成（E2E N/N）通过、回归锁就位（详见 test-report）"
```

测试不过、或四类测试有任一类既没做又没声明 N/A，不许进入下一步——这是 verification-before-completion 的硬约束。**回归测试不是可选项**：E2E 套件必须是项目内固定可复跑的文件（不是跑完即弃的临时脚本），修过的每个 bug 都加一条回归锁。

## Step 3: api-docs —— 文档

**Web 分支（有网络 API）**：

1. **`docs/api.md`**（项目根目录下）：按**实际实现**同步 Phase 5 的 api.md——端点、参数、状态码、错误格式，每个端点附一条可直接执行的 curl 示例。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤、测试命令、部署入口（指向 Phase 8，写"见 .productflow 流水线 Phase 8"即可，不展开）。
3. 把 docs/api.md 复制为过程产物并登记，操作台展示接口文档：

```bash
cp docs/api.md .productflow/artifacts/phase-7/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/api-docs.md --title "API 接口文档"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 api-docs --status done
```

**iOS 分支（P-iOS，无网络 API）**：纯本地 App 没有 HTTP 端点，本步改为给**数据层 + 本地服务**留文档：

1. **`docs/data-model.md`**（项目根目录下）：列出实际落地的 SwiftData `@Model` 类——每个实体的字段、关系（`@Relationship`）、唯一性约束在哪段写入逻辑里保证；若有 `Services/` 下的 `protocol`，写清各方法的输入/输出/副作用（替代 curl 示例）。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤（Xcode 打开、选 scheme/Simulator 跑）、测试命令（`xcodebuild test ...`）、上架入口（指向 Phase 8，写"见 .productflow 流水线 Phase 8（archive → TestFlight）"即可，不展开）。
3. 把 docs/data-model.md 复制为过程产物并登记，操作台展示数据层文档（artifact 标题用"数据模型文档"以区分 Web 的接口文档）：

```bash
cp docs/data-model.md .productflow/artifacts/phase-7/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/api-docs.md --title "数据模型文档（SwiftData @Model）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 api-docs --status done
```

（产物文件名仍用 `api-docs.md` 以与现有 step/检查点登记一致；iOS 项目里它装的是数据模型文档。）

**Android 分支（P-Android，无网络 API）**：纯本地 App 没有 HTTP 端点，本步改为给**数据层 + 本地服务**留文档：

1. **`docs/data-model.md`**（项目根目录下）：列出实际落地的 Room `@Entity` 与 `@Dao`——每个实体的字段、关系（外键/联结表）、`@Index(unique = true)` 或写入查重逻辑在哪里保证；若有 Repository `interface`，写清各方法的输入/输出/副作用（替代 curl 示例）；有 schema 迁移（`Migration`）时列出版本与变更。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤（Android Studio 打开、选 AVD 跑，或 `./gradlew installDebug` + `adb shell am start`）、测试命令（`./gradlew test`、`./gradlew connectedAndroidTest`）、上架入口（指向 Phase 8，写"见 .productflow 流水线 Phase 8（AAB 上传 Play Console）"即可，不展开）。
3. 把 docs/data-model.md 复制为过程产物并登记，操作台展示数据层文档（artifact 标题用"数据模型文档"以区分 Web 的接口文档）：

```bash
cp docs/data-model.md .productflow/artifacts/phase-7/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/api-docs.md --title "数据模型文档（Room @Entity/@Dao）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 7 api-docs --status done
```

（产物文件名仍用 `api-docs.md` 以与现有 step/检查点登记一致；Android 项目里它装的是数据模型文档。）

**Desktop 分支（P-Desktop，无网络 API，数据层 = SQLite）**：桌面 App 没有 HTTP 端点，本步改为给**数据层 + 本地 Tauri command**留文档：

1. **`docs/data-model.md`**（项目根目录下）：列出实际落地的 SQLite 表结构（同 Web 的 schema.sql，但以桌面应用视角描述）——每张表的字段、类型、`UNIQUE` 约束/索引；若有 Tauri `#[tauri::command]` 或 Electron `ipcMain` handler，写清各方法的输入/输出/副作用（替代 curl 示例）。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤（`cargo tauri dev` 或 `npm run start`）、测试命令（`cargo test`、`npm run test`、`npm run test:e2e`）、打包入口（`cargo tauri build` 生成安装包，指向 Phase 8，写"见 .productflow 流水线 Phase 8（tauri build/安装包）"即可，不展开）。
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

2. 写本阶段汇总 `artifacts/phase-7/build-summary.md`（一页：后端技术栈与目录结构、已实现清单【Web=端点清单 / iOS=`@Model` 数据层清单 / Android=Room `@Entity`/`@Dao` 清单 / Desktop=SQLite 表清单】、测试结果摘要（四类：单元/接口集成/E2E/回归）、文档位置、已知限制），并登记：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" artifact 7 artifacts/phase-7/build-summary.md --title "Phase 7 后端实现·测试汇总"
   ```

3. 确认 backend、unit-test、integration-test、api-docs 四个 step 均为 done、test-report.md + api-docs.md（iOS/Android/Desktop 为数据模型文档）+ build-summary.md 均已登记（有后端项目还应确认 `docs/design.md` 设计方案文档已产出）。**⑦ 不做 impl-check**——那套「④ 每页×平台都有实现截图」的页面覆盖硬闸是 ⑥ 前端阶段的门禁（见 `phase-6-frontend.md`），不属于后端阶段。

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" phase 7 --status done
   python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 7 完成：后端+测试+文档就绪，待用户确认进入部署"
   ```

4. 在 CLI 向用户汇报：测试通过情况、文档位置（Web=API 文档 / iOS=数据模型文档 / Android=数据模型文档 / Desktop=SQLite 数据模型文档），请用户在网页或 CLI 确认后进入 Phase 8（Web=部署 CF Pages/Worker/单机；iOS=archive → 上传 TestFlight，提审前停手；Android=AAB 上传 Play Console，提审前停手；Desktop=`cargo tauri build` 生成安装包，可选上架商店；见 phase-8-deploy.md）。用户此前明确说过"全自动"则不停留，直接进入 Phase 8。
