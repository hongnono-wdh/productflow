# Phase 6：开发实现

何时读本文件：Phase 5 已 done、用户确认进入开发阶段时。本阶段把设计稿和数据设计变成可运行、测过、有文档的产品代码。

## 输入（开工前确认齐全）

- `artifacts/phase-4/direction.md` —— 最终设计方向（色板/字体/区块顺序），前端唯一依据
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
python3 "$SKILL_DIR/scripts/pf_state.py" phase 6 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 6 开发实现开始"
```

## 全阶段纪律（贯穿每一步）

- **动手前**：调用 test-driven-development skill。关键路径先写测试（红），再写实现（绿）。Web 测关键 API 端点和表单提交；iOS 测模型/持久化逻辑与核心交互旅程；Android 测 ViewModel/纯逻辑（JUnit）与 Room 持久化往返及核心交互旅程（Compose UI Test / Espresso）；Desktop 测前端逻辑（Vitest/Jest）+ Rust 核心逻辑（`cargo test`）+ SQLite 持久化往返（写→重启应用→读回）+ 桌面旅程（`tauri-driver`/WebDriver 或前端 Playwright）。落地页/纯展示页不必给每个静态区块写测试，测"会坏且坏了有后果"的部分：表单校验、API 返回、数据写入（iOS 对应：写入查重、SwiftData 持久化、关键视图状态；Android 对应：写入查重、Room 持久化、关键 Compose 视图状态；Desktop 对应：写入查重（SQL UNIQUE/索引）、SQLite 持久化跨重启、关键桌面 UI 状态）。
- **说"完成"前**：调用 verification-before-completion skill。所有测试真正跑过（Web `npm run test:e2e`；iOS `xcodebuild test`；Android `./gradlew test` + `./gradlew connectedAndroidTest`；Desktop `cargo test` + 前端测试 + E2E）、截图真正生成，才更新 step 为 done。没跑过的东西不登记。
- **出 bug**：调用 systematic-debugging skill，先复现、定位根因，再修。禁止盲改重试。

## 调试期沟通与开调试现场（贯穿构建/调试，不只收尾）

本阶段构建/调试往往是长循环，**沟通和"开给用户看"要贯穿整个调试期，别全攒到阶段收尾那个检查点**。下面这套与现有「阶段收尾 checkpoint 的 inbox/reply」「preview-feedback 圈选反馈在检查点定位修复」「systematic-debugging 先复现再修」不矛盾，是把它们**提前到调试进行中**用。

### 1. 调试期双向沟通（别攒到阶段收尾才沟通）

- **频繁读 inbox**：长时间构建/调试时，**每个调试迭代之间、卡住时、做完一个有意义子步后**都看一眼用户留言——用户在操作台 💬 随时可发，别只在阶段收尾那个检查点才读。**频繁瞄一眼用 `inbox --peek`（只看、不推进已读游标，方便反复回看上下文）；真要处理某条时再 `inbox` 消费 + `reply` 回应**：

  ```bash
  python3 "$SKILL_DIR/scripts/pf_state.py" inbox --peek   # 频繁瞄一眼：只看不推进游标
  python3 "$SKILL_DIR/scripts/pf_state.py" inbox          # 要处理时才用：读取并推进已读游标
  python3 "$SKILL_DIR/scripts/pf_state.py" reply "<对该条留言的回应：已按你说的调 X / 这点我先记下，等当前这步跑完处理>"
  ```

- **该用户拍板的歧义，调试中就用 `choice ask` + `choice wait` 暂停问**：调试里遇到**该让用户拍板的歧义**（行为取舍、A 还是 B、某处设计不确定），或**需要用户看一眼现场再决定**时，抛选项并**接着阻塞等回答**，拿到答复再改，别自己瞎猜跑下去：

  ```bash
  ID=$(python3 "$SKILL_DIR/scripts/pf_state.py" choice ask --stage 6 \
        --question "登录失败时是停在当前页报错，还是跳回登录页？" \
        --option "A：原页报错" --option "B：跳回登录页")
  python3 "$SKILL_DIR/scripts/pf_state.py" choice wait "$ID" --timeout 600
  ```

  抛出后操作台会显示「⏳ Agent 正等你回答」状态，用户答完自动继续。**`wait` 退出码恒为 0（成功/超时都是 0）——必须解析它打印的 stdout JSON 判断**：拿到答复是 `{"answer":"X"}`，超时是 `{"timeout":true,"answer":null}`，别靠 `$?` 判超时。拿到答复再改；超时才按手册决策树自己定一个并 `reply` 说明理由。

- **频繁 `log` 进展**：经常 `log` 一句"当前在调什么 / 进展到哪"，让用户跟得上——操作台有运行状态 + 日志流，用户据此知道你没卡死、在推进哪条线：

  ```bash
  python3 "$SKILL_DIR/scripts/pf_state.py" log "正在调表单提交：服务端校验已通，现查 E2E 里 toast 不可见的根因"
  ```

### 2. 把调试现场开给用户看（本机本地，能看见，不只截图）

操作台跑在**用户本机**、agent 就是用户机器上的 shell——可以把运行中的产物**直接弹到用户屏幕上实时看**，不止 headless 截图。这让"模拟打开调试 + 调试中沟通"在 Phase 6 **进行中**就成立（用户实时看到运行产物 + 随时留言/圈选 + agent 用 `choice` 暂停问你），不必等阶段完成。

⚠️ **仅当 agent 在能访问用户桌面 GUI 的本机会话时才弹窗**（本机 macOS 从用户终端起的 server 通常可以）。跑在远端/无显示环境（Ubuntu/root 服务器、无 `DISPLAY` 的后台进程）时 `open` / `xdg-open` / `open -a Simulator` / `emulator` / `cargo tauri dev` 会失败——这种情况**跳过弹窗**，改为只用 `reply` 把 `http://localhost:$PORT` 或复现方法告诉用户让其自行打开（或 `ssh -L` 端口转发），**别让 open/emulator/tauri dev 失败把流水线带成 command error**（同 iOS 缺 Xcode、Android 缺 Android Studio、Desktop 缺 Rust/Tauri 时"停下说明、别硬跑"的防御姿态）。

- **Web 分支**：起 dev server 后，把它弹进用户浏览器让用户实时看，并把 URL 用 `log`/`reply` 告诉用户：

  ```bash
  # 起 dev server（按预设：npm run dev / wrangler dev 等），拿到本地端口 PORT 后
  open "http://localhost:$PORT"            # macOS；Linux 用 xdg-open "http://localhost:$PORT"
  python3 "$SKILL_DIR/scripts/pf_state.py" reply "已起 dev server，你可以自己开 http://localhost:$PORT 实时看，我这边继续调"
  ```

  这是"额外让用户能看"，**不替代** headless 截图与可复跑 E2E——继续照常用 **Python Playwright（chromium headless）** 截图存档、跑 Step 4 的可复跑测试。

- **iOS 分支（P-iOS）**：把模拟器开到用户屏幕上，用户能实时看到 App 在跑；agent 照常驱动 + `xcrun simctl io booted screenshot` 截图存档：

  ```bash
  xcrun simctl boot "iPhone 15"            # 启一台目标机型（已 boot 可跳过）
  open -a Simulator                        # 让模拟器窗口出现在用户屏幕上
  python3 "$SKILL_DIR/scripts/pf_state.py" reply "模拟器已开到你屏幕上，App 正在跑，你可以直接看，我继续调"
  ```

- **Android 分支（P-Android）**：把 Emulator（AVD）开到用户屏幕上，用户能实时看到 App 在跑；agent 照常驱动 + `adb exec-out screencap` 截图存档。**仅当有 GUI 的本机会话时**才弹 Emulator 窗口；远端/无显示环境跳过弹窗，只 `reply` 告知用户如何本地复现：

  ```bash
  # 先确认 AVD 名称（列出可用 AVD）
  emulator -list-avds
  # 启动 Emulator（后台运行，窗口出现在用户屏幕上）
  emulator -avd <avd_name> &
  # 等设备就绪
  adb wait-for-device
  # 安装并启动 App
  ./gradlew installDebug
  adb shell am start -n <包名>/<主 Activity 名>
  python3 "$SKILL_DIR/scripts/pf_state.py" reply "Emulator 已开到你屏幕上，App 正在跑，你可以直接看，我继续调"
  ```

- **Desktop 分支（P-Desktop）**：本机起桌面应用原生窗口，弹到用户屏幕上实时看；agent 照常驱动 + Playwright webview 截图 / 系统截图存档。**仅当有 GUI 的本机会话时**才起原生窗口；远端/无显示环境跳过弹窗，只 `reply` 告知用户如何本地复现（`cargo tauri dev` 或 `npm run start`），**别让命令失败带成 command error**：

  ```bash
  # Tauri（推荐）：起桌面应用开发模式，原生窗口出现在用户屏幕上
  cargo tauri dev
  # 或 npm run tauri dev（视项目 package.json 配置）
  python3 "$SKILL_DIR/scripts/pf_state.py" reply "桌面应用窗口已弹到你屏幕上，你可以直接看，我继续调"

  # 无 Rust 时 Electron 等价：
  # npm run start   （或 electron .）
  ```

  等窗口起来后再 reply 告知用户；远端/无显示环境只 reply 复现方法，别让命令失败。

## ultracode 实现模式（本阶段构建首选）

本阶段开发实现**优先用 ultracode（Workflow 多代理编排）**，不要单线程串行把代码从头写到尾：

- **拆任务并行推进**：把构建拆成相互独立、可并行的任务——前端/界面、后端/数据层、各功能模块、测试各自一条线推进，能并行就并行，而不是一个 step 写完再写下一个。模块间有契约依赖（如接口契约、`@Model` 结构）的，以 Phase 5 已定的单一事实来源对齐，避免并行时各写各的对不上。
- **对抗式验证**：实现完不要自说自话"写完了"——用**独立 agent 复核代码 + 真正跑测试**来确认。沿用本阶段「四类测试 + test-report 门禁」，用多代理把覆盖做厚（不同 agent 分别补单元/集成/E2E/回归，比单线程更容易把漏网路径测到）。
- **四条分支都适用**：Web、iOS、Android、Desktop 一样拆并行——iOS 可把视图（SwiftUI）/数据层（SwiftData `@Model`）/XCTest/XCUITest 拆成并行任务推进；Android 可把 Compose 视图/数据层（Room `@Entity`/`@Dao`）/JUnit/Compose UI Test 拆成并行任务推进；Desktop 可把 Web 前端界面（复用 ④ 设计）/Rust 壳（Tauri commands）/SQLite 数据层/E2E（`tauri-driver`/前端 Playwright）拆成并行任务推进。
- **降级**：headless 后台 agent 若拿不到 Workflow 工具（ultracode 不可用），就退到用 Task 子代理 / 单线程把活做扎实——不硬依赖 ultracode，但有就用。下面各 step 的纪律、门禁、命令在两种模式下都不变。

## Step 1: scaffold —— 脚手架

按 template-choice.md 选定的预设搭工程，目录结构严格以 templates.md 中该预设的定义为准，不要自创结构（后续阶段和部署/上架脚本依赖这个结构）。

**产品代码放项目根目录**。`.productflow/` 只放过程产物（截图、报告、状态），不放任何会被部署或 git 管理的产品代码——部署和版本管理都针对项目根。

**Web 分支（T1/T2/T3）**：搭前端目录 + 后端/Worker（按档），装依赖。完成标志：依赖装好、dev server 能起、空页面能访问。

**iOS 分支（P-iOS）**：建 Xcode 工程（SwiftUI App 模板），按 templates.md 的 P-iOS 树搭 `MyApp/`（`MyAppApp.swift` 标 `@main`、挂 `.modelContainer(for:)`）+ `Models/`、`Views/`、可选 `ViewModels/`/`Services/` + `MyAppTests/`（XCTest）+ `MyAppUITests/`（XCUITest），依赖用 **SPM**（不引 CocoaPods）。
- **前置检测**（缺了提示用户装 Xcode / 命令行工具，别硬跑报 command not found）：`xcodebuild -version`、`xcrun simctl list devices`。检测不到 Xcode 时停下，在 CLI 说明"需要装 Xcode 才能继续 iOS 构建"，不要把流水线跑成一串 `command not found`。
- 完成标志：`xcodebuild build` 能编过、空 App 能在 Simulator 起来、`ModelContainer` 挂载成功（一个空 `@Model` 也行）。

**Android 分支（P-Android）**：建 Gradle 工程（Compose Activity 模板，Kotlin DSL），按 templates.md 的 P-Android 树搭 `app/src/main/java/<pkg>/`（`data/`、`ui/`、`viewmodel/`、`MainActivity.kt`），在 `build.gradle.kts` 引入 Room + Compose 依赖。
- **前置检测**（缺了提示用户装 Android Studio / SDK / 命令行工具，别硬跑报 command not found）：`./gradlew --version`、`adb --version`、`emulator -list-avds`。检测不到时停下，在 CLI 说明"需要装 Android Studio 及 SDK 才能继续 Android 构建"，不要把流水线跑成一串 `command not found`。
- 完成标志：`./gradlew assembleDebug` 能编过、空 App 能在 Emulator 起来、Room `@Database` 能建库挂载成功。

**Desktop 分支（P-Desktop）**：建 Tauri 工程（推荐），**复用 ④ 设计的 Web 前端当界面**（HTML/CSS/JS 放 `src/` 或 `frontend/`，Tauri `src-tauri/` 放 Rust 壳），在 `src-tauri/Cargo.toml` 引入 `tauri-plugin-sql`（SQLite）+ `rusqlite`；按 templates.md 的 P-Desktop 树搭目录结构。无 Rust 时用 Electron 等价（`electron-builder`，数据层用 `better-sqlite3`）。
- **前置检测**（缺了提示用户装对应工具，别硬跑报 command not found）：Tauri → `rustc --version`、`cargo --version`、`cargo tauri --version`（macOS 需 Xcode CLT、Windows 需 MSVC）；Electron → `node --version`、`npx electron --version`。检测不到时停下，在 CLI 说明"需要装 Rust + Cargo + Tauri CLI 才能继续 Desktop 构建"，不要把流水线跑成一串 `command not found`。
- 完成标志：`cargo tauri build` 能编过（或 `cargo tauri dev` 能起空窗口）、SQLite 库能建表挂载（跑 `artifacts/phase-5/schema.sql` DDL 建库成功）。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 scaffold --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "脚手架完成，dev server 可启动 / iOS 空 App 可在 Simulator 启动 / Android 空 App 可在 Emulator 启动 / Desktop 空窗口可在本机起来（按平台取其一）"
```

## Step 2: frontend —— 前端 / 界面实现

（用 ultracode 时，前端/界面与 Step 3 后端/数据层可并行推进，不必等后端完工再动前端。）

严格按 direction.md 落地：色板色值逐个对、字体与字号层级照搬、区块顺序不增不减不调换。direction.md 是 Phase 4 用户确认过的结论，临场"优化"等于推翻用户决定；确有实现障碍（如字体无法商用），在 CLI 说明并征求意见。

**iOS 分支（P-iOS）**：界面用 **SwiftUI** 视图实现，按 direction.md 的色板/字体/区块顺序落进各 `Views/` 文件（色值用 `Color(hex:)`/资产目录，字体层级照搬到 `.font(...)`）；产品 UI 性质的界面参照下面"产品 UI"那条选 skill。下面的"落地页交付质量底线"是 Web 营销页专属（移动端导航/SEO meta/裸 href 等是 web 概念），iOS App 不适用——iOS 的质量底线在 Step 4 的 XCUITest 旅程与 Simulator 截图里把关。其余 step 2 内容（截图登记、preview-feedback 圈选反馈）iOS 同样适用，见本步末尾的 iOS 截图说明。

**Android 分支（P-Android）**：界面用 **Jetpack Compose** 实现，按 direction.md 的色板/字体/区块顺序落进各 Composable 文件（色值映射到 `MaterialTheme.colorScheme`/自定义 Color，字体层级照搬到 `TextStyle`/`MaterialTheme.typography`）；产品 UI 性质的界面参照下面"产品 UI"那条选 skill。下面的"落地页交付质量底线"是 Web 营销页专属，Android App 不适用——Android 的质量底线在 Step 4 的 Compose UI Test / Espresso 旅程与 Emulator 截图里把关。其余 step 2 内容（截图登记、preview-feedback 圈选反馈）Android 同样适用，见本步末尾的 Android 截图说明。

**Desktop 分支（P-Desktop）**：界面**复用 ④ 设计的 Web 前端**（HTML/CSS/JS），按 direction.md 的色板/字体/区块顺序落地到 `src/`（或 `frontend/`）下各页面文件；Tauri webview 渲染这套 Web 前端作为桌面应用界面；产品 UI 性质的界面参照下面"产品 UI"那条选 skill。下面的"落地页交付质量底线"是 Web 营销页专属，桌面应用不适用——Desktop 的质量底线在 Step 4 的 `tauri-driver`/Playwright E2E 旅程与桌面窗口截图里把关。其余 step 2 内容（截图登记、preview-feedback 圈选反馈）Desktop 同样适用，见本步末尾的 Desktop 截图说明。

按页面类型选 skill，不要混用：

- 落地页 / 营销页 → `design-taste-frontend`
- 产品 UI（dashboard / 表单页 / admin / **iOS App 界面** / **Android App 界面** / **桌面应用界面**）→ `frontend-design` 或 `ui-ux-pro-max`（design-taste-frontend 自身声明产品 UI out of scope）

**落地页交付质量底线**（dogfood 实测：三个生成项目都漏了下面这几项，逐条过一遍再标 done）：
- **移动端导航可用**：导航不能在窄屏直接 `display:none` 就完事——给汉堡菜单/可达的区块跳转（带 `aria-expanded`/`aria-controls`），并在 E2E 加一个移动视口（如 390×844）旅程断言导航可达。
- **SEO / 社交分享 meta**：`title`+`description` 之外补 `canonical`、`og:title/og:description/og:image`、`twitter:card=summary_large_image`、`theme-color`；营销页缺 og:image 会让分享卡片没图。favicon 也要有。
- **a11y 基线**：`<main>` landmark + skip-link、表单控件有 `<label>`、可折叠/动态区用 `aria-expanded`/`aria-live`、加 `@media (prefers-reduced-motion: reduce)` 关掉强制动画。
- **没有占位/死链**：CTA、文档、社交链接不能指向 `https://github.com` 这类裸占位或编造的数据（如假 star 数）——要么真实地址，要么"即将上线"页；可在 E2E 加一条断言无裸占位 href。

完成后对运行中的界面截图，存入 `artifacts/phase-6/`（相对 `.productflow/`）并登记——操作台靠这些图向用户展示成品。

**⚠️ 视觉还原比对（前端门禁，最容易被跳过、直接决定"前端效果行不行"）**：实现的界面**不是写完截个图就算 done**——必须对着设计稿**一一比对、迭代到位**，否则还原效果差：

1. 把实现的界面截图（同视口/同尺寸：Web 桌面 ~1440 / 移动 ~390；iOS 用对应机型 Simulator；Android 用对应 AVD（Emulator）截图（`adb exec-out screencap -p > x.png`）；Desktop 对运行中的桌面窗口截图——Playwright 截 webview，或系统截图（macOS `screencapture -x preview-desktop.png`））。
2. **并排比对「实现截图」vs「④ 页面设计稿」**——设计稿在 `artifacts/phase-4/`（对应该页该平台的稿；首页/基调可参照 ③ 定稿首图 `artifacts/phase-3/heroes/<定稿>`）。你是**有视觉能力的 Claude**：用 `Read` 同时打开「实现截图」和「设计稿」两张图，**逐项核对并列出每一处差异**——整体布局 / 区块顺序 / 间距与留白 / 配色（逐个 hex 比）/ 字体·字号·字重·行高 / 圆角·阴影 / 组件样式与状态 / 图标 / 图片与占位。
3. **按差异改样式 → 重新截图 → 再比对，迭代到「实现与设计稿高度一致」为止**——不是"差不多就行"：`direction.md` / 设计稿是 Phase 4 用户确认过的合同，颜色、间距、字体必须对得上。**这一步没做，就是用户说的"还原效果差、前端不行"。**
4. **比对对齐后**才标 `frontend --status done`；把"实现截图 + 对应设计稿"一并登记，用户在操作台能对比验收。

> Web、iOS、Android、Desktop 都要做这一步（iOS 对着 ④ 对应平台稿 + ③ 基调，用 Simulator 截图比对；Android 同理用 Emulator 截图比对；Desktop 用桌面窗口截图——Playwright webview 截图或 `screencapture`——同视口比对 ④ 设计稿）。圈选反馈（preview-feedback）是用户帮你挑漏的，但**主动一一比对是你的本职**，别等用户圈。

**Web 分支截图**：对运行中的页面截图（桌面端约 1440px 宽、移动端约 390px 宽，截全页）。**浏览器工具**：操作台触发的是 headless 后台 agent，没有浏览器 MCP——截图和 E2E 直接用本机已装的 **Python Playwright（chromium headless）** 写脚本（或 webapp-testing / playwright-cli skill），别去 ToolSearch 找 MCP：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-desktop.png --title "成品预览（桌面端）"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-mobile.png --title "成品预览（移动端）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 frontend --status done
```

**iOS 分支截图**：在 Simulator 里把核心屏跑起来，用 `xcrun simctl io booted screenshot` 截图（替代 Playwright），存入 `artifacts/phase-6/` 并登记。至少截两张代表性界面（如首屏 + 一个核心功能屏）：

```bash
xcrun simctl io booted screenshot "$PF_DIR/artifacts/phase-6/preview-home.png"
xcrun simctl io booted screenshot "$PF_DIR/artifacts/phase-6/preview-detail.png"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-home.png --title "成品预览（iOS 首屏）"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-detail.png --title "成品预览（iOS 核心屏）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 frontend --status done
```

（`booted` 指当前已启动的模拟器；先 `xcrun simctl boot` 一台目标机型，或用 Xcode 打开后再截。`$PF_DIR` 即项目 `.productflow/` 绝对路径。）

**Android 分支截图**：在 Emulator 里把核心屏跑起来，用 `adb exec-out screencap -p` 截图（替代 Playwright / xcrun），存入 `artifacts/phase-6/` 并登记。至少截两张代表性界面（如首屏 + 一个核心功能屏）：

```bash
adb exec-out screencap -p > "$PF_DIR/artifacts/phase-6/preview-home.png"
adb exec-out screencap -p > "$PF_DIR/artifacts/phase-6/preview-detail.png"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-home.png --title "成品预览（Android 首屏）"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-detail.png --title "成品预览（Android 核心屏）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 frontend --status done
```

（`adb exec-out screencap -p` 把 Emulator 当前屏幕截成 PNG 输出到 stdout；先确保 Emulator 已启动且 App 已 `installDebug` 并拉起。`$PF_DIR` 即项目 `.productflow/` 绝对路径。）

**Desktop 分支截图**：对运行中的桌面窗口截图——优先用 Playwright 截 webview（headless/headed 均可），或用系统截图（macOS `screencapture`）；存入 `artifacts/phase-6/` 并登记。至少截两张代表性界面（如首屏 + 一个核心功能屏）：

```bash
# 方式 A：Playwright 截 webview（需 cargo tauri dev 已起，webview 暴露 DevTools port）
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.connect_over_cdp('http://localhost:<devtools_port>')
    page = b.contexts[0].pages[0]
    page.screenshot(path='$PF_DIR/artifacts/phase-6/preview-desktop-home.png', full_page=True)
    b.close()
"

# 方式 B：系统截图（macOS，窗口已在屏幕上）
screencapture -x "$PF_DIR/artifacts/phase-6/preview-desktop-home.png"
screencapture -x "$PF_DIR/artifacts/phase-6/preview-desktop-detail.png"

python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-desktop-home.png --title "成品预览（Desktop 首屏）"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-desktop-detail.png --title "成品预览（Desktop 核心屏）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 frontend --status done
```

（先确保 `cargo tauri dev` 或 `npm run start` 已起、桌面窗口已显示；`$PF_DIR` 即项目 `.productflow/` 绝对路径。远端/无 GUI 环境跳过截图弹窗，只 reply 告知用户本地自行打开并截图。）

这两张截图登记后，用户能在操作台⑥**点开圈选**有问题的区域并写意见。这类反馈通过 inbox 的 `type:"preview-feedback"` 进来，正文形如「成品预览反馈 @ 标题（文件），N 处：1. 区域(左25% 上30% 宽40% 高25%)：这里按钮太小…」——`pf_state inbox` 即可读到。检查点读到时**逐条按区域定位修复**（区域坐标是相对截图的百分比，可映射回对应页面元素）后 `reply` 回应，别忽略。

## Step 3: backend —— 后端 / 数据层实现

**Web 分支（T2/T3 有后端；T1 纯静态本步可标 skipped 或仅实现表单 Function）**：

1. 用 schema.sql 建库（SQLite 系：T2 为 D1、T3 为 better-sqlite3，以 template-choice.md 为准），不要在建库时顺手改表结构；发现 DDL 有问题，先更新 Phase 5 的 schema.sql 再执行，保持单一事实来源。
2. 按 api.md 逐个实现端点。实现与契约出现偏差时，以实际实现为准并在 Step 5 同步回文档。
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
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 backend --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "后端端点实现完成，服务端校验与防滥用就位 / iOS 数据层 @Model 就位，写入查重保唯一 / Android 数据层 Room @Entity/@Dao 就位，写入查重保唯一 / Desktop SQLite 数据层就位，schema.sql 已建库，查重保唯一（按平台取其一）"
```

## Step 4: testing —— 测试

两层测试，全部真实跑过。Web 主线见下；**iOS 分支见本步末尾的"iOS 测试分支"**（XCTest + XCUITest 在 Simulator 跑）；**Android 分支见本步末尾的"Android 测试分支"**（JUnit + Espresso/Compose UI Test 在 Emulator 跑）；**Desktop 分支见本步末尾的"Desktop 测试分支（P-Desktop）"**（前端 Vitest/Jest + Rust `cargo test` + `tauri-driver`/Playwright E2E），四类测试门禁四条分支共用。（用 ultracode 时，让独立 agent 复核代码并把四类测试分头并行做厚，对抗式确认而非自说自话——见上文「ultracode 实现模式」。）调试这层往往是长循环：**按上文「调试期沟通与开调试现场」边调边读 `inbox`、卡在歧义点用 `choice ask`+`wait` 暂停问、并把在跑的产物实时开给用户看**，别把沟通攒到阶段收尾。

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

**测试小结产物（门禁，必做）**：把这次测试情况写成 `artifacts/phase-6/test-report.md` 并登记——对**四类测试逐一表态**：① 单元 ② 接口集成 ③ 端到端(E2E) ④ 核心功能回归。每类要么「✅ 通过（写清测了什么、几条、复跑命令）」，要么「N/A（一句理由，如 T1 纯静态无后端 → 单元/接口集成 N/A）」。iOS 四类映射：①=XCTest，②=SwiftData 持久化往返，③=XCUITest 旅程，④=XCUITest 回归锁（iOS 项目这四类一般都该有实测，"无网络 API"不等于免测——②落到持久化往返而非接口）。Android 四类映射：①=JUnit（ViewModel/纯逻辑），②=Room 持久化往返，③=Compose UI Test / Espresso 旅程，④=Compose UI Test / JUnit 回归锁（Android 项目这四类一般都该有实测，"无网络 API"不等于免测——②落到 Room 持久化往返而非接口）。Desktop 四类映射：①=前端 Vitest/Jest + Rust `cargo test`，②=SQLite 持久化往返（写→重启→读回），③=`tauri-driver`/Playwright E2E 旅程，④=回归测试锁（Desktop 项目这四类一般都该有实测，"无网络 API"不等于免测——②落到 SQLite 持久化往返而非接口）。**不允许某类既不做、也不声明 N/A**——静默跳过测试是这条流水线最容易漏的坑。这份 test-report 会显示在操作台，是「测试做没做、做到什么程度」**唯一可审计的凭证**（流水线不靠 agent 一句口头"测过了"放行）。

测试全绿、且 test-report 四类都已表态后：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/test-report.md --title "测试小结（单元/集成/E2E/回归）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 testing --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "测试全绿：E2E N/N 通过、回归锁就位（详见 test-report）"
```

测试不过、或四类测试有任一类既没做又没声明 N/A，不许进入下一步——这是 verification-before-completion 的硬约束。**回归测试不是可选项**：E2E 套件必须是项目内固定可复跑的文件（不是跑完即弃的临时脚本），修过的每个 bug 都加一条回归锁。

## Step 5: api-docs —— 文档

**Web 分支（有网络 API）**：

1. **`docs/api.md`**（项目根目录下）：按**实际实现**同步 Phase 5 的 api.md——端点、参数、状态码、错误格式，每个端点附一条可直接执行的 curl 示例。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤、测试命令、部署入口（指向 Phase 7，写"见 .productflow 流水线 Phase 7"即可，不展开）。
3. 把 docs/api.md 复制为过程产物并登记，操作台展示接口文档：

```bash
cp docs/api.md .productflow/artifacts/phase-6/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/api-docs.md --title "API 接口文档"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 api-docs --status done
```

**iOS 分支（P-iOS，无网络 API）**：纯本地 App 没有 HTTP 端点，本步改为给**数据层 + 本地服务**留文档：

1. **`docs/data-model.md`**（项目根目录下）：列出实际落地的 SwiftData `@Model` 类——每个实体的字段、关系（`@Relationship`）、唯一性约束在哪段写入逻辑里保证；若有 `Services/` 下的 `protocol`，写清各方法的输入/输出/副作用（替代 curl 示例）。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤（Xcode 打开、选 scheme/Simulator 跑）、测试命令（`xcodebuild test ...`）、上架入口（指向 Phase 7，写"见 .productflow 流水线 Phase 7（archive → TestFlight）"即可，不展开）。
3. 把 docs/data-model.md 复制为过程产物并登记，操作台展示数据层文档（artifact 标题用"数据模型文档"以区分 Web 的接口文档）：

```bash
cp docs/data-model.md .productflow/artifacts/phase-6/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/api-docs.md --title "数据模型文档（SwiftData @Model）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 api-docs --status done
```

（产物文件名仍用 `api-docs.md` 以与现有 step/检查点登记一致；iOS 项目里它装的是数据模型文档。）

**Android 分支（P-Android，无网络 API）**：纯本地 App 没有 HTTP 端点，本步改为给**数据层 + 本地服务**留文档：

1. **`docs/data-model.md`**（项目根目录下）：列出实际落地的 Room `@Entity` 与 `@Dao`——每个实体的字段、关系（外键/联结表）、`@Index(unique = true)` 或写入查重逻辑在哪里保证；若有 Repository `interface`，写清各方法的输入/输出/副作用（替代 curl 示例）；有 schema 迁移（`Migration`）时列出版本与变更。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤（Android Studio 打开、选 AVD 跑，或 `./gradlew installDebug` + `adb shell am start`）、测试命令（`./gradlew test`、`./gradlew connectedAndroidTest`）、上架入口（指向 Phase 7，写"见 .productflow 流水线 Phase 7（AAB 上传 Play Console）"即可，不展开）。
3. 把 docs/data-model.md 复制为过程产物并登记，操作台展示数据层文档（artifact 标题用"数据模型文档"以区分 Web 的接口文档）：

```bash
cp docs/data-model.md .productflow/artifacts/phase-6/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/api-docs.md --title "数据模型文档（Room @Entity/@Dao）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 api-docs --status done
```

（产物文件名仍用 `api-docs.md` 以与现有 step/检查点登记一致；Android 项目里它装的是数据模型文档。）

**Desktop 分支（P-Desktop，无网络 API，数据层 = SQLite）**：桌面 App 没有 HTTP 端点，本步改为给**数据层 + 本地 Tauri command**留文档：

1. **`docs/data-model.md`**（项目根目录下）：列出实际落地的 SQLite 表结构（同 Web 的 schema.sql，但以桌面应用视角描述）——每张表的字段、类型、`UNIQUE` 约束/索引；若有 Tauri `#[tauri::command]` 或 Electron `ipcMain` handler，写清各方法的输入/输出/副作用（替代 curl 示例）。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤（`cargo tauri dev` 或 `npm run start`）、测试命令（`cargo test`、`npm run test`、`npm run test:e2e`）、打包入口（`cargo tauri build` 生成安装包，指向 Phase 7，写"见 .productflow 流水线 Phase 7（tauri build/安装包）"即可，不展开）。
3. 把 docs/data-model.md 复制为过程产物并登记，操作台展示数据层文档（artifact 标题用"数据模型文档"以区分 Web 的接口文档）：

```bash
cp docs/data-model.md .productflow/artifacts/phase-6/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/api-docs.md --title "数据模型文档（SQLite 表结构）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 api-docs --status done
```

（产物文件名仍用 `api-docs.md` 以与现有 step/检查点登记一致；Desktop 项目里它装的是 SQLite 数据模型文档。）

## 检查点（阶段收尾，顺序执行）

1. 读网页端消息并逐条回应（有改动要求就先处理再收尾）：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" inbox
   python3 "$SKILL_DIR/scripts/pf_state.py" reply "<对该条留言的回应>"   # 每条留言各回一次
   ```

2. 写本阶段汇总 `artifacts/phase-6/build-summary.md`（一页：技术栈与目录结构、已实现清单【Web=端点清单 / iOS=屏与 `@Model` 清单 / Android=屏与 Room 实体清单 / Desktop=窗口/屏与 SQLite 表清单】、测试结果摘要、已知限制），并登记：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/build-summary.md --title "Phase 6 实现汇总"
   ```

3. 确认 5 个 step 均为 done、预览截图（Web 桌面+移动 / iOS 两张代表屏 / Android 两张代表屏 / Desktop 两张代表屏）+ api-docs.md（iOS/Android/Desktop 为数据模型文档）+ build-summary.md 均已登记，然后：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" phase 6 --status done
   python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 6 完成：实现+测试+文档就绪，待用户确认进入部署"
   ```

4. 在 CLI 向用户汇报：成品预览截图位置、测试通过情况、文档位置（Web=API 文档 / iOS=数据模型文档 / Android=数据模型文档 / Desktop=SQLite 数据模型文档），请用户在网页或 CLI 确认后进入 Phase 7（Web=部署 CF Pages/Worker/单机；iOS=archive → 上传 TestFlight，提审前停手；Android=AAB 上传 Play Console，提审前停手；Desktop=`cargo tauri build` 生成安装包，可选上架商店；见 phase-7-deploy.md）。用户此前明确说过"全自动"则不停留，直接进入 Phase 7。
