# Phase 8：测试

何时读本文件：Phase 6（前端实现）+ Phase 7（后端实现）已 done、前端 + 后端 + 契约都在、进入测试阶段时。本阶段对**真实拼装后的产物**做完整验证：**集成测试 + E2E 端到端旅程 + 回归 + 前后端契约一致性 + test-report 门禁 + 整体流程评审**。①单元测试已在 ⑦ 做（后端逻辑，fake 适配器 / 内存库，快、隔离）；本阶段做的是 ②③④——**拼装后的真品才测得出的东西**。下一阶段是 ⑨ 部署上线（见 `phase-9-deploy.md`）。

> **无后端项目**（DEC-5 判无后端：纯静态 / 纯前端、原生本地 App）：⑦ 已隐藏，本阶段做**前端集成 / E2E**（原生 App 做本地数据层持久化往返 + UI 旅程）——"前端即全部"，同样要真跑通、不走过场。

## 输入（开工前确认齐全）

- ⑥ 的前端产物（④ 每页 × 平台已实现、可运行）
- ⑦ 的后端产物（接口 + 数据层已实现、后端单元测试已过）+ `docs/api.md` 契约（涉后端项目）
- `artifacts/phase-5/` 的 api.md / schema / **core-analysis.mm.md**（E2E 旅程与契约的单一事实来源）
- `artifacts/phase-5/template-choice.md` —— 决定走 Web、iOS、Android 还是 Desktop 测试分支

平台分支：读 template-choice.md 里登记的平台与预设——`PC/H5` 走下文 Web 主线（@playwright/test 或 Python Playwright）；`APP` 按预设走各步里标注的 **iOS 分支**（XCTest + XCUITest 在 Simulator 跑）/ **Android 分支**（JUnit + Espresso/Compose UI Test 在 Emulator 跑）；`PC` 预设为 `P-Desktop` 走 **Desktop 分支**（Rust `cargo test` + `tauri-driver`/Playwright E2E）。下面每个 step 先给 Web 主线，平台专属的集成 / E2E / 回归见末尾「平台测试分支」，不要混用工具链。

阶段开始：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 8 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 8 测试开始：对拼装后的真实产物做集成 + E2E + 回归"
```

> **共享实现纪律见 ⑥**：本阶段与 ⑥ 前端实现、⑦ 后端实现共用一套实现纪律——**调试期沟通与开调试现场（边调边读 inbox、`choice ask`+`wait` 暂停问、把在跑的产物实时开给用户看）**、**ultracode 实现模式（多代理并行把测试做厚 + 对抗式验证）** 两节均见 `phase-6-frontend.md` 对应章节，本文件不重复；verification-before-completion（真跑过才登记）/ systematic-debugging（先复现再修）同样适用。测试这层往往是长循环，别把沟通攒到阶段收尾。

## 整体流程评审（集成前 · 涉后端项目）

> **DEC-5 前置**：无后端项目（纯静态 T1 / 原生本地）跳过本节，只 `log` 一句「本项目无后端，跳过整体流程评审」，照常走下面的 step。有后端（T2/T3、带云后端的桌面等）才做。

**整体流程评审**（⑦ 全部模块 done、本阶段集成时）：独立 agent 审**整个前后端流程 + 连接闭环**——所有页面 / 前端流程 + 所有后端接口流程 + 页面↔接口↔数据的连接、有无孤儿 / 契约不一致 / 数据不通，以**系统流程图（`.productflow/backend-flow.json`）+ 页面地图 + ER** 为面。这是 ⑦ 模块级评审（单模块代码 + 测试 + 契约一致性）之上的**系统级**一遍：审出问题回 ⑦ 或前端修，改完再集成。**若动了接口契约 → 触发契约变更传播**（同步改所有依赖该接口的前后端 + 相关测试）。

## 测挂 → 在系统流程图上回修（过程可见，别闷头改）

本阶段测出的问题，回修要**在操作台可见**——让用户看到「哪个模块/接口挂了、正在修、修好了」，而不是只看到 ⑧ 一直在跑。每类测试挂了就这么走：

1. **定位 + 标红**：从失败用例反推是哪个模块 / 接口（auth 的 E2E 挂 = `module:auth`），标测试态 `fail`（⑧ 测试进度即变红）+ `proc` 脉冲 + `log` 说清挂在哪：
   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow set-test --id module:auth --status fail --note "退出后停在注册 tab（应回登录页）"   # --note 写清「为什么挂」，测试进度直接显示
   python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow proc --id module:auth --state on   # 回修=改代码，proc 亮「处理中」（⑤⑦ 开发视图也会亮，因为真在改代码）；改完重测时用 set-test --status testing、别继续用 proc
   python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" log "auth 模块 E2E 挂了（退出后停在注册 tab），正在回修"
   ```
2. **改代码**：按 systematic-debugging 复现 → 根因 → 改（后端 bug 直接改后端、前端 bug 改前端——改代码不受阶段限制，⑧ 发现 ⑦ 的后端问题就当场改后端，等于回 ⑦ 修）。
3. **修好转绿**：该模块相关测试重新跑绿后——转测试态 `pass`、清脉冲：
   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow set-test --id module:auth --status pass
   python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow proc --id module:auth --state off
   python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" log "auth 回修完成：退出 → 登录旅程重新跑绿，回归锁已加"
   ```

操作台上就是一条可见的线：**测挂 → 挂的模块标红(needfix) → 处理中脉冲 → 修好转绿**。⑧ 测试页也显示这份模块进度（不用切回 ⑤ 的系统流程图）。无后端项目同理，标前端相关的模块 / 页面节点。

## 需第三方 key 的测试点 → 缺 key 就判失败并说明，不阻塞后续（别 mock 掩盖）

有些模块的测试必须真调第三方服务（短信登录要发验证码、支付要真下单等），依赖 ⑤ 登记、用户在操作台填的第三方 key。**测某模块前先看它有没有登记 key、key 填了没**：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" product-key list   # 看登记了哪些 key、归属哪个模块、是否已填
```

- **登记了 key 但用户没填**（secrets 里没值、环境变量为空）→ **别 mock 假装通过**（那会把"缺 key"这个真问题掩盖掉），直接把该测试点判失败、说清原因、继续跑别的：
  ```bash
  python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow set-test --id module:auth --status fail
  python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" log "auth「获取验证码」测试失败：需要 SMS_ACCESS_KEY_ID（阿里云短信），用户尚未在操作台填此 key——非代码问题，填好后重测这一项"
  ```
- **继续跑其它测试**——别因为一个模块缺 key 就停整个 ⑧；不依赖该 key 的模块照常测、照常绿。
- **test-report 里如实写**：该项写「❌ 失败：缺 X key（用户未配置，非代码问题）」——不是 N/A、更不是假装通过。操作台上就是：缺 key 的模块标红 + 日志说清缺哪个 key、去哪填，用户填完重测这一项即可。

> 真调会产生副作用 / 费用的（真发短信、真扣款）用服务商**沙箱 / 测试凭证**、不用生产 key；沙箱凭证同样走 product-key 登记 + 用户填，缺了同上处理（判失败 + 说明）。

## 测试态用 set-test 标记（独立于 ⑦ 开发态，重做自动重头）+ 配了真 key 就真测

**开测标「测试中」、测完标结果**——⑧ 独立的测试态（和 ⑦ 的 `set-status` 开发态分开）：开测 `set-test --status testing`（操作台显示「测试中」）、测完 `set-test --status pass`（通过）/ `fail`（挂）。**跑测试一律用 `set-test`、绝不用 `proc`**——`proc` 是「agent 在改这个节点代码」的信号、⑤⑦ 开发视图也读它，拿它标「测试中」会让 ⑤⑦ 误显示处理中（proc 只留给「回修=真改代码」）。操作台「测试进度」据此显示：
```bash
python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_DIR" backend-flow set-test --id module:auth --status pass   # 或 fail
```
**重做 ⑧ 时系统自动清空测试态、进度重头**（全回「待测」），绝不复用上轮的 pass/fail——所以别以为「上次绿了这次就不用测」，每次重做都从头验。

**依赖第三方的模块——用户填了 key 就切真 provider 真测**（真发短信 / 沙箱真下单），验证端到端真能跑通，而不是只 mock；没填 key → 按上文「缺 key 判失败」。**key 填了但是错的**（真调鉴权失败 / 签名不对）→ `set-test --status fail` + `log「auth 模块 SMS key 鉴权失败：key 不对或已过期，请在操作台重填」`——测试进度标红、**明确提示是 key 不对**（而不是含糊说「测试挂了」，让用户以为是代码 bug）。

## Step 1: integration-test —— 集成测试

对**真实拼装后的产物**（前端 + 后端一起、或原生 App 的界面 + 本地数据层）做集成验证——不是 mock、不是单进程内存库，是拼起来的真品能不能跑通。

- **API 集成**：前端真的调后端、后端真的读写库，端到端一条链路通（不是 ⑦ 里 fake 适配器的单元级）。每条关键链路覆盖成功路径 + 一个失败路径（如必填缺失返回 4xx、错误提示可见）。
- **前后端契约一致性**：按 ⑤ / `docs/api.md` 契约逐个核对——请求 / 响应字段、状态码、错误格式前后端对得上；发现不一致就地修并同步文档（文档与实现不符比没有文档更糟）。
- **数据持久化验证**（凡有持久化的项目必做）：在真实部署形态上「写一条 → 重启服务 / 容器 → 读回来」，确认数据真落盘。内存库和单进程生命周期内的测试都测不出持久化问题——历史事故：SQLite 的 **WAL 日志模式在 Docker Desktop(macOS) 的 bind mount 上写入不落盘**（虚拟文件系统不支持 WAL 的共享内存 mmap），注册"成功"但重启即丢、跨连接查不到。修复是 `journal_mode = DELETE`，并加一条「重开连接后数据仍在」的回归测试锁住（回归锁登记在 Step 3）。选 SQLite + 容器 + bind mount 时尤其要测这一项。**iOS = SwiftData 持久化往返 / Android = Room 持久化往返 / Desktop = SQLite 持久化往返**——详见末尾平台分支。

集成测试落成项目内固定可复跑的测试文件（**临时脚本不算测试**——它跑完即弃、下个 bug 照漏）。全绿后：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 8 integration-test --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "集成测试全绿：真实拼装产物端到端跑通、契约一致、数据持久化落盘验证通过"
```

## Step 2: e2e-test —— E2E 端到端旅程

E2E 用户旅程测试（Web @playwright/test，落为项目内可复跑的测试文件如 `tests/e2e/journeys.spec.*` + `npm run test:e2e`——**临时截图脚本不算测试**，它跑完就消失，下个 bug 照样漏网）。**非 Node 项目**（T1 纯静态没有 npm 工具链，或原生 App）别因为没 Node 就退回一次性脚本——落成等价的可复跑测试文件：Web 纯静态用 **Python Playwright（`from playwright.sync_api import sync_playwright`，chromium headless）** 写 `tests/e2e/test_journeys.py`（自起本地 HTTP server / BASE_URL 可指向容器）；iOS 用 XCUITest、Android 用 Compose UI Test / Espresso、Desktop 用 `tauri-driver`/Playwright（见末尾平台分支）。作用一致：固定、可复跑、跑在真实产物上。旅程清单的来源固定三处：

1. **auth/会话全循环**：注册 → 进入 → 退出 → 登录 → 再进入（历史教训：只测注册不测"退出再登录"，曾让"退出后停在注册 tab"的 bug 直接漏到用户手上）；
2. **core-analysis.mm.md 的傻瓜式路径**逐步走通——那是产品对用户的核心承诺，承诺本身必须有测试锁住；
3. **每个表单/弹窗的失败路径**：错误提示必须"可见"（断言 toBeVisible 而非仅存在——hidden 属性被 CSS display 顶掉是真实发生过的事故）。

E2E 必须跑在**真实最终产物**上（容器或构建产物，BASE_URL 可配置），不是 dev server——旅程测试的意义就是验证拼装后的真品。共享实例的旅程测试用 `workers: 1` 串行，避免互踩和触发限流。**移动端 Web** 补一个移动视口（如 390×844）旅程断言导航可达；**落地页 / 营销页**补一条断言无裸占位 href（承接 ⑥「落地页交付质量底线」，在真产物上验证）。修过的每个 bug 加一条回归锁用例（登记在 Step 3）。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 8 e2e-test --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "E2E 端到端旅程全绿：会话全循环 + 核心承诺路径 + 表单失败提示可见，跑在真实产物上"
```

## Step 3: regression —— 回归测试

**回归测试不是可选项**：本阶段（以及此前 ⑥⑦ 调试）修过的**每个 bug 都加一条回归锁用例**，注释里写明历史事故，纳入项目内固定可复跑的测试套件（不是跑完即弃的临时脚本）。Step 1 的「重开连接 / 重启后数据仍在」持久化验证也落一条回归锁。

- **验收纪律**：自查 / 验收一律跑仓库里的正式测试套件（Web `npm test` + `npm run test:e2e`；iOS `xcodebuild test`；Android `./gradlew test` + `./gradlew connectedAndroidTest`；Desktop `cargo test` + 前端测试 + E2E），**不要现场手写一次性脚本来"走一遍看看"**——临时脚本会凭记忆猜元素 id/选择器（猜错就是假失败，浪费来回），且跑完即弃、下个 bug 照漏。要覆盖新交互就扩充正式套件：动笔前先确认真实的元素标识（Web `grep` DOM 的 id/role；iOS 用 `accessibilityIdentifier` 标记控件，XCUITest 按 id 取；Android 用 `Modifier.testTag` 或 `contentDescription`，Compose UI Test 按 tag 取），再写进测试文件。

把集成 / E2E / 回归的复跑命令补进项目根目录 README（承接 ⑦ 已写的单元测试命令），让任何人不读代码就能复跑全套。全绿后：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 8 regression --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "回归锁就位：修过的每个 bug 各一条回归用例，纳入正式套件、可复跑"
```

## 平台测试分支（iOS / Android / Desktop 的集成 + E2E + 回归）

Web 主线见上；原生 / 桌面按下面分支落地 Step 1-3 的 ②集成 ③E2E ④回归（①单元已在 ⑦）。所有测试落成项目内可复跑文件——**临时脚本不算测试**，跟 Web 同纪律。

### iOS 测试分支（P-iOS）

测试器是 **iOS Simulator**，命令是 `xcodebuild test`（指定 `-scheme` + `-destination 'platform=iOS Simulator,name=iPhone 15'` 之类）；模拟器开关 / 重置用 `xcrun simctl`。**前置检测** `xcodebuild -version`、`xcrun simctl list devices`，缺了提示装 Xcode，别硬跑。落成项目内 `MyAppTests/`（XCTest）/ `MyAppUITests/`（XCUITest）下可复跑的文件。

- **②集成 = SwiftData 持久化往返**（凡有持久化必做，对应 Web 的"写→重启→读回"）：在 XCTest 里建**临时** `ModelContainer`（`isStoredInMemoryOnly: false` 指向临时目录，或新建独立 container），「写一条 → 重建 `ModelContext`/`ModelContainer` → 读回」，断言数据仍在、字段一致、唯一性约束生效。内存里写完直接读不算往返——必须跨 context/container 重建才测得出真落盘。
- **③E2E = XCUITest 旅程**：core-analysis.mm.md 的傻瓜式路径在 Simulator 上点通（新建 → 保存 → **杀掉并重开 App 数据仍在** → 编辑 → 删除等核心循环）。控件用 `accessibilityIdentifier` 标记后按 id 取；断言用 `XCTAssert(element.exists)` / `waitForExistence`，别靠屏幕坐标硬点。旅程清单来源同上文三处（会话/状态全循环、核心承诺路径、每个表单弹窗的失败提示可见）。
- **④回归 = 修过的 bug 加 XCUITest 锁**：每个修过的 bug 补一条 XCUITest（或 XCTest，视 bug 层级），注释写明历史事故；跑完即弃的临时脚本不算。

iOS 端的"E2E 跑在真实最终产物上"= 用 **Release 配置**或与上架一致的构建跑 XCUITest，别只测 Debug。

### Android 测试分支（P-Android）

测试器是 **Android Emulator（AVD）**，仪器测试命令 `./gradlew connectedAndroidTest`（需 Emulator/真机；`./gradlew test` 的单元层已在 ⑦）。**前置检测** `./gradlew --version`、`adb --version`、`emulator -list-avds`，缺了提示装 Android Studio / SDK，别硬跑。落成项目内 `app/src/androidTest/`（仪器测试）下可复跑文件。

- **②集成 = Room 持久化往返**（凡有持久化必做，对应 Web 的"写→重启→读回"）：在 JUnit 仪器测试里用 `Room.inMemoryDatabaseBuilder` 建临时库（或真实库写→重建/重启→读回），「写一条 → 重建 Database 实例 → 读回」，断言数据仍在、字段一致、唯一性约束生效。内存库写完直接读不算往返——必须跨实例重建才测得出真落盘。
- **③E2E = Compose UI Test / Espresso 旅程**：core-analysis.mm.md 的傻瓜式路径在 Emulator 上点通（新建 → 保存 → **杀进程重开 App 数据仍在** → 编辑 → 删除等核心循环）。控件用 `Modifier.testTag` 或 `contentDescription` 标记后用 `onNodeWithTag`/`onNodeWithContentDescription` 取；断言用 `assertIsDisplayed()`/`assertExists()`。旅程清单来源同上文三处。
- **④回归 = 修过的 bug 加 Compose UI Test / JUnit 锁**：每个修过的 bug 补一条测试（视 bug 层级选单元或仪器测试），注释写明历史事故；跑完即弃的临时脚本不算。

Android 端的"E2E 跑在真实最终产物上"= 用 **Release 构建**（`./gradlew assembleRelease` + installRelease）跑 connectedAndroidTest，别只测 Debug。

### Desktop 测试分支（P-Desktop）

测试器是桌面旅程（`tauri-driver`+WebDriver，或前端 Playwright 跑渲染层）+ Rust 集成测试。**前置检测** `rustc --version`、`cargo --version`、`cargo tauri --version`，缺了提示装 Rust/Tauri CLI，别硬跑。落成项目内可复跑文件（前端 `tests/`；Rust `src-tauri/tests/`）。

- **②集成 = 本地 SQLite 持久化往返**（凡有持久化必做，对应 Web 的"写→重启→读回"）：「写一条 → 重启应用 → 读回」，断言数据仍在、字段一致、唯一性约束生效（SQL UNIQUE 索引）。Tauri 可用 Rust 集成测试直接操 `rusqlite`；Electron 用 Jest + `better-sqlite3` 建临时库测往返。内存里写完直接读不算往返——必须跨进程重启才测得出真落盘。
- **③E2E = 桌面应用旅程**：core-analysis.mm.md 的傻瓜式路径在桌面窗口上走通（新建 → 保存 → **重启应用数据仍在** → 编辑 → 删除等核心循环）。优先用 `tauri-driver`+WebDriver（`WebDriver::new`）驱动；无驱动则退化为前端 Playwright 跑渲染层旅程（`cargo tauri dev` 先起，再 Playwright 连 webview DevTools port）。旅程清单来源同上文三处。
- **④回归 = 修过的 bug 加测试锁**：每个修过的 bug 补一条测试（视 bug 层级选前端单元/Rust 单元/E2E），注释写明历史事故；跑完即弃的临时脚本不算。

Desktop 端的"E2E 跑在真实最终产物上"= 用 **Release 构建**（`cargo tauri build`）跑 E2E，别只测 dev 模式。

## Step 4: test-report —— 测试报告门禁（必做）

把这次测试情况写成 `artifacts/phase-8/test-report.md` 并登记——对**四类测试逐一表态**：① 单元（⑦ 做的后端单元测试，本报告汇总结论）② 接口集成 ③ 端到端(E2E) ④ 核心功能回归。每类要么「✅ 通过（写清测了什么、几条、复跑命令）」，要么「N/A（一句理由，如 T1 纯静态无后端 → 单元/接口集成 N/A）」。iOS 四类映射：①=XCTest（⑦），②=SwiftData 持久化往返，③=XCUITest 旅程，④=XCUITest 回归锁（iOS 项目这四类一般都该有实测，"无网络 API"不等于免测——②落到持久化往返而非接口）。Android 四类映射：①=JUnit（⑦，ViewModel/纯逻辑），②=Room 持久化往返，③=Compose UI Test / Espresso 旅程，④=Compose UI Test / JUnit 回归锁。Desktop 四类映射：①=前端 Vitest/Jest + Rust `cargo test`（⑦），②=SQLite 持久化往返（写→重启→读回），③=`tauri-driver`/Playwright E2E 旅程，④=回归测试锁。**不允许某类既不做、也不声明 N/A**——静默跳过测试是这条流水线最容易漏的坑。这份 test-report 会显示在操作台，是「测试做没做、做到什么程度」**唯一可审计的凭证**（流水线不靠 agent 一句口头"测过了"放行）。

四类都已表态、且 ②③④ 真跑绿后：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 8 artifacts/phase-8/test-report.md --title "测试报告（单元/集成/E2E/回归）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 8 test-report --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "测试报告门禁通过：单元(⑦) + 集成 + E2E + 回归四类均已表态、②③④ 全绿（详见 test-report）"
```

测试不过、或四类测试有任一类既没做又没声明 N/A，不许进入下一步——这是 verification-before-completion 的硬约束。

## 检查点（阶段收尾，顺序执行）

1. 读网页端消息并逐条回应（有改动要求就先处理再收尾）：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" inbox
   python3 "$SKILL_DIR/scripts/pf_state.py" reply "<对该条留言的回应>"   # 每条留言各回一次
   ```

2. 确认本阶段各 step（integration-test、e2e-test、regression、test-report）均为 done、`artifacts/phase-8/test-report.md` 已登记（四类逐一表态、②③④ 真跑绿）。

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" phase 8 --status done
   python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 8 完成：集成 + E2E + 回归全绿、test-report 门禁通过，待用户确认进入 ⑨ 部署"
   ```

3. 在 CLI 向用户汇报：四类测试通过情况（指向 test-report）、已知限制，请用户在网页或 CLI 确认后进入 ⑨ 部署上线（Web=部署 CF Pages/Worker/单机；iOS=archive → 上传 TestFlight，提审前停手；Android=AAB 上传 Play Console，提审前停手；Desktop=`cargo tauri build` 生成安装包，可选上架商店；见 `phase-9-deploy.md`）。用户此前明确说过"全自动"则不停留，直接进入 ⑨ 部署。
