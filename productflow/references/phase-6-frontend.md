# Phase 6：前端实现

何时读本文件：Phase 5（功能与数据设计）已 done、进入实现阶段时。本阶段把 ④ 设计稿变成**可运行的前端**（脚手架 + 前端页面 / 交互 + 本地预览）。后端实现 + 测试是下一个阶段 ⑦（见 `phase-7-backend.md`）。

## 输入（开工前确认齐全）

- `artifacts/phase-4/direction.md` —— 最终设计方向（色板 / 字体 / 区块顺序），前端唯一依据
- `artifacts/phase-4/` 各页面设计稿（pages.json + 各平台版本）
- `artifacts/phase-5/template-choice.md` —— 选定的预设（含平台与栈），决定本阶段走 Web、iOS、Android 还是 Desktop 分支
- templates.md —— 各预设的目录结构基准与各阶段衔接（脚手架据此搭建）

平台分支：读 template-choice.md 里登记的平台与预设——`PC/H5` 走下文 Web 主线；`APP` 按预设分 **iOS 分支**（Xcode/SwiftUI）/ **Android 分支**（Gradle/Kotlin/Jetpack Compose）；`PC` 预设为 `P-Desktop` 时走 **Desktop 分支**（Tauri/Rust + 复用 ④ Web 前端）。下面每个 step 先给 Web 主线，再给 iOS、Android、Desktop 分支，不要混用工具链。

阶段开始：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 6 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 6 前端实现开始"
```

## 全阶段纪律（贯穿每一步）

> 本节「全阶段纪律 / 调试期沟通与开调试现场 / ultracode 实现模式」三节是 ⑥ 前端实现与 ⑦ 后端实现·测试**共用的实现纪律**（放在先跑的 ⑥ 这里，⑦ 回读本文件对应章节即可，不重复造）。

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

操作台跑在**用户本机**、agent 就是用户机器上的 shell——可以把运行中的产物**直接弹到用户屏幕上实时看**，不止 headless 截图。这让"模拟打开调试 + 调试中沟通"在**本阶段（实现）进行中**就成立（用户实时看到运行产物 + 随时留言/圈选 + agent 用 `choice` 暂停问你），不必等阶段完成。

> **操作台「预览」按钮（`/api/run-action` → 后台 spawn 本动作）**：⑥⑦ 实现面板有一个按平台自适应的「📱构建并在模拟器预览 / 🖥本地运行预览 / 🌐本地预览」按钮，用户点它就是要你**只做本节这件事**——把当前已实现的产品按平台构建并起到他屏幕/模拟器上，不重做/推进整个阶段、不标任何 step/phase done、不改产品代码。起好后 `reply` 告诉他怎么看。下面按平台给做法。

⚠️ **仅当 agent 在能访问用户桌面 GUI 的本机会话时才弹窗**（本机 macOS 从用户终端起的 server 通常可以）。跑在远端/无显示环境（Ubuntu/root 服务器、无 `DISPLAY` 的后台进程）时 `open` / `xdg-open` / `open -a Simulator` / `emulator` / `cargo tauri dev` 会失败——这种情况**跳过弹窗**，改为只用 `reply` 把 `http://localhost:$PORT` 或复现方法告诉用户让其自行打开（或 `ssh -L` 端口转发），**别让 open/emulator/tauri dev 失败把流水线带成 command error**（同 iOS 缺 Xcode、Android 缺 Android Studio、Desktop 缺 Rust/Tauri 时"停下说明、别硬跑"的防御姿态）。

- **Web 分支**：起 dev server 后，把它弹进用户浏览器让用户实时看，并把 URL 用 `log`/`reply` 告诉用户：

  ```bash
  # 起 dev server（按预设：npm run dev / wrangler dev 等），拿到本地端口 PORT 后
  open "http://localhost:$PORT"            # macOS；Linux 用 xdg-open "http://localhost:$PORT"
  python3 "$SKILL_DIR/scripts/pf_state.py" reply "已起 dev server，你可以自己开 http://localhost:$PORT 实时看，我这边继续调"
  ```

  这是"额外让用户能看"，**不替代** headless 截图与可复跑 E2E——继续照常用 **Python Playwright（chromium headless）** 截图存档、跑测试步的可复跑测试。

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

> **阶段归属**：脚手架（Step 1）+ 前端（Step 2）是本阶段（⑥ 前端实现）的两步活。后端（按 ⑤ 契约实现并对接前端）、单元 + 集成测试、文档在 ⑦ 后端实现·测试阶段做（见 `phase-7-backend.md`）；**无后端项目**（DEC-5 判无后端）⑦ 隐藏，单元 + 集成测试并入本阶段（见下文「测试（无后端项目）」）。

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

**⓪ pre-flight + 用 design-spec 实现（还原度方案专题 A/B · R-⑥a/b）——本步开头先做**：

1. **pre-flight 硬门**：先校验 design-spec 就绪（组件库已锁、无悬空/成环 token），缺则**停下补 ②④、别裸写**：
   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" spec check   # 有 error 先回 ②/④ 补，不硬写
   ```
2. **编译 token 到三端**（一份 token → CSS/Swift/Compose，三端一致是编译产物、不靠手抄）：
   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" spec compile --platform all --out artifacts/phase-6/tokens
   ```
   把产物 token 文件放进项目（Web `tokens.css` / iOS `Tokens.swift` / Android `Tokens.kt`），界面**引用 token、不硬编码色值/间距**。
3. **按组件映射拼、不肉眼临摹**：读 `spec show` 的 `pages[].components`（④ 定的「设计元素→组件」映射）+ `artifacts/phase-2/component-catalog.md`，**用同款组件库组件拼页面**（目录里没有的才定制）；营销页 `type=marketing` 按骨架组件 + `assets[]` 素材嵌入。
4. **分治：逐组件/区块实现**（不整页一次临摹——整图直出最易漏元素）：一个组件/区块一次，实现 → 核对 → 下一个。
5. **逐态实现**：按 `pages[].states` 把组件的交互态/数据态（default/hover/focus/disabled/loading/empty…）都实现，别只做 default（专题 D）。

> design-spec 是 ⑥ 的机器依据（PNG 只作预览对照）；下面的 direction.md / 设计稿是人读参照与视觉比对基准。


（用 ultracode 时，前端/界面与后端/数据层（⑦ 阶段）可并行推进，不必等后端完工再动前端。）

严格按 direction.md 落地：色板色值逐个对、字体与字号层级照搬、区块顺序不增不减不调换。direction.md 是 Phase 4 用户确认过的结论，临场"优化"等于推翻用户决定；确有实现障碍（如字体无法商用），在 CLI 说明并征求意见。

**iOS 分支（P-iOS）**：界面用 **SwiftUI** 视图实现，按 direction.md 的色板/字体/区块顺序落进各 `Views/` 文件（色值用 `Color(hex:)`/资产目录，字体层级照搬到 `.font(...)`）；产品 UI 性质的界面参照下面"产品 UI"那条选 skill。下面的"落地页交付质量底线"是 Web 营销页专属（移动端导航/SEO meta/裸 href 等是 web 概念），iOS App 不适用——iOS 的质量底线在测试步的 XCUITest 旅程与 Simulator 截图里把关。其余 step 2 内容（截图登记、preview-feedback 圈选反馈）iOS 同样适用，见本步末尾的 iOS 截图说明。

**Android 分支（P-Android）**：界面用 **Jetpack Compose** 实现，按 direction.md 的色板/字体/区块顺序落进各 Composable 文件（色值映射到 `MaterialTheme.colorScheme`/自定义 Color，字体层级照搬到 `TextStyle`/`MaterialTheme.typography`）；产品 UI 性质的界面参照下面"产品 UI"那条选 skill。下面的"落地页交付质量底线"是 Web 营销页专属，Android App 不适用——Android 的质量底线在测试步的 Compose UI Test / Espresso 旅程与 Emulator 截图里把关。其余 step 2 内容（截图登记、preview-feedback 圈选反馈）Android 同样适用，见本步末尾的 Android 截图说明。

**Desktop 分支（P-Desktop）**：界面**复用 ④ 设计的 Web 前端**（HTML/CSS/JS），按 direction.md 的色板/字体/区块顺序落地到 `src/`（或 `frontend/`）下各页面文件；Tauri webview 渲染这套 Web 前端作为桌面应用界面；产品 UI 性质的界面参照下面"产品 UI"那条选 skill。下面的"落地页交付质量底线"是 Web 营销页专属，桌面应用不适用——Desktop 的质量底线在测试步的 `tauri-driver`/Playwright E2E 旅程与桌面窗口截图里把关。其余 step 2 内容（截图登记、preview-feedback 圈选反馈）Desktop 同样适用，见本步末尾的 Desktop 截图说明。

按页面类型选 skill，不要混用：

- 落地页 / 营销页 → `design-taste-frontend`
- 产品 UI（dashboard / 表单页 / admin / **iOS App 界面** / **Android App 界面** / **桌面应用界面**）→ `frontend-design` 或 `ui-ux-pro-max`（design-taste-frontend 自身声明产品 UI out of scope）

**落地页交付质量底线**（dogfood 实测：三个生成项目都漏了下面这几项，逐条过一遍再标 done）：
- **移动端导航可用**：导航不能在窄屏直接 `display:none` 就完事——给汉堡菜单/可达的区块跳转（带 `aria-expanded`/`aria-controls`），并在 E2E 加一个移动视口（如 390×844）旅程断言导航可达。
- **SEO / 社交分享 meta**：`title`+`description` 之外补 `canonical`、`og:title/og:description/og:image`、`twitter:card=summary_large_image`、`theme-color`；营销页缺 og:image 会让分享卡片没图。favicon 也要有。
- **a11y 基线**：`<main>` landmark + skip-link、表单控件有 `<label>`、可折叠/动态区用 `aria-expanded`/`aria-live`、加 `@media (prefers-reduced-motion: reduce)` 关掉强制动画。
- **没有占位/死链**：CTA、文档、社交链接不能指向 `https://github.com` 这类裸占位或编造的数据（如假 star 数）——要么真实地址，要么"即将上线"页；可在 E2E 加一条断言无裸占位 href。

完成后**对运行中的界面按 ④ 页面清单逐页截图**，存入 `artifacts/phase-6/`（相对 `.productflow/`）并登记——操作台靠这些图向用户展示成品，并按页把「④ 设计稿 ↔ ⑥ 实现截图」并排给用户对比 UI 还原度。

**逐页截图（关键，别只截「代表性两张」）**：要覆盖 ④ 设计过的**每一个页面 × 每个选定平台**，一页都不能漏——

1. `python3 "$SKILL_DIR/scripts/pf_state.py" page list` 读出所有页面（`pg-xxx` id + 页面名 + 各平台 version），据此规划要截哪些页、哪些平台。
2. 逐页把该页在对应平台跑起来、截图（文件名建议 `preview-<页名>-<平台>.png`；重做同一页复用同名覆盖，见下方「截图卫生」）。
3. **登记时带 `--page-id <pg-xxx> --platform <PC|H5|APP>`**（原生 App 无论 iOS/Android 平台均记 `APP`，用 `--title` 区分是哪端）——操作台据此把这张实现图与 ④ 该页该平台的设计稿**精确配对、并排展示**。**漏带 `--page-id` 的截图**不进对比、只落到操作台的「其它成品预览」平铺区。

**⚠️ 视觉还原比对（前端门禁，最容易被跳过、直接决定"前端效果行不行"）**：实现的界面**不是写完截个图就算 done**——必须对着设计稿**一一比对、迭代到位**，否则还原效果差：

1. 把实现的界面截图（同视口/同尺寸：Web 桌面 ~1440 / 移动 ~390；iOS 用对应机型 Simulator；Android 用对应 AVD（Emulator）截图（`adb exec-out screencap -p > x.png`）；Desktop 对运行中的桌面窗口截图——Playwright 截 webview，或系统截图（macOS `screencapture -x preview-desktop.png`））。
2. **并排比对「实现截图」vs「④ 页面设计稿」**——设计稿在 `artifacts/phase-4/`（对应该页该平台的稿；首页/基调可参照 ③ 定稿首图 `artifacts/phase-3/heroes/<定稿>`）。你是**有视觉能力的 Claude**：用 `Read` 同时打开「实现截图」和「设计稿」两张图，**逐项核对并列出每一处差异**——整体布局 / 区块顺序 / 间距与留白 / 配色（逐个 hex 比）/ 字体·字号·字重·行高 / 圆角·阴影 / 组件样式与状态 / 图标 / 图片与占位。
3. **按差异改样式 → 重新截图 → 再比对，迭代到「实现与设计稿高度一致」为止**——不是"差不多就行"：`direction.md` / 设计稿是 Phase 4 用户确认过的合同，颜色、间距、字体必须对得上。**这一步没做，就是用户说的"还原效果差、前端不行"。**
4. **比对对齐后**才标 `frontend --status done`；把每张实现截图**带 `--page-id`/`--platform`** 登记（对齐 ④ 页面），用户在操作台就能看到「④ 设计稿 ↔ ⑥ 实现截图」按页并排、逐页验收还原度。

> Web、iOS、Android、Desktop 都要做这一步（iOS 对着 ④ 对应平台稿 + ③ 基调，用 Simulator 截图比对；Android 同理用 Emulator 截图比对；Desktop 用桌面窗口截图——Playwright webview 截图或 `screencapture`——同视口比对 ④ 设计稿）。圈选反馈（preview-feedback）是用户帮你挑漏的，但**主动一一比对是你的本职**，别等用户圈。

**重做/重新出图时的截图卫生（避免新旧混淆）**：同一个屏/页重做后，**复用同一稳定文件名覆盖**（如某屏始终叫 `preview-home.png`，别迭代成 `preview-home-v2.png`），然后**重新跑一次 `artifact` 登记**——登记按文件路径去重、刷新时间戳，操作台只显示最新一张、并自动绕过浏览器缓存（不重登记则前端可能仍显示缓存里的旧图）。若某张截图对应的页面**被删掉/方案作废**、文件名又确实变了，用 `pf_state.py artifact-rm <阶段> <旧文件>` 撤销登记并删掉旧文件，别让画廊里留着已经不算数的旧截图。

**Web 分支截图**：对运行中的页面截图（桌面端约 1440px 宽、移动端约 390px 宽，截全页）。**浏览器工具**：操作台触发的是 headless 后台 agent，没有浏览器 MCP——截图和 E2E 直接用本机已装的 **Python Playwright（chromium headless）** 写脚本（或 webapp-testing / playwright-cli skill），别去 ToolSearch 找 MCP：

**逐页截**（`page list` 里每页 × 每个选定平台各一张：PC 视口 ~1440、H5 视口 ~390），登记带 `--page-id`/`--platform` 与 ④ 页面对齐。示例（首页 `pg-home` 出了 PC + H5 两版，其余页照此循环，一页不漏）：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-home-pc.png --title "首页（PC 实现）" --page-id pg-home --platform PC
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-home-h5.png --title "首页（H5 实现）" --page-id pg-home --platform H5
# …对 page list 里每一页、每个选定平台重复上面两行…
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 frontend --status done
```

**iOS 分支截图**：在 Simulator 里**按 ④ 页面清单逐屏**跑起来，用 `xcrun simctl io booted screenshot` 截图（替代 Playwright），存入 `artifacts/phase-6/` 并登记。**逐页截、一页不漏**（原生 App 平台记 `APP`，`--title` 标 iOS 以区分）。示例（首页 `pg-home`、详情页 `pg-detail`，其余页照此循环）：

```bash
xcrun simctl io booted screenshot "$PF_DIR/artifacts/phase-6/preview-home-ios.png"
xcrun simctl io booted screenshot "$PF_DIR/artifacts/phase-6/preview-detail-ios.png"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-home-ios.png --title "首页（iOS 实现）" --page-id pg-home --platform APP
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-detail-ios.png --title "详情页（iOS 实现）" --page-id pg-detail --platform APP
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 frontend --status done
```

（`booted` 指当前已启动的模拟器；先 `xcrun simctl boot` 一台目标机型，或用 Xcode 打开后再截。`$PF_DIR` 即项目 `.productflow/` 绝对路径。）

**Android 分支截图**：在 Emulator 里**按 ④ 页面清单逐屏**跑起来，用 `adb exec-out screencap -p` 截图（替代 Playwright / xcrun），存入 `artifacts/phase-6/` 并登记。**逐页截、一页不漏**（原生 App 平台记 `APP`，`--title` 标 Android 以区分）。示例（首页 `pg-home`、详情页 `pg-detail`，其余页照此循环）：

```bash
adb exec-out screencap -p > "$PF_DIR/artifacts/phase-6/preview-home-android.png"
adb exec-out screencap -p > "$PF_DIR/artifacts/phase-6/preview-detail-android.png"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-home-android.png --title "首页（Android 实现）" --page-id pg-home --platform APP
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-detail-android.png --title "详情页（Android 实现）" --page-id pg-detail --platform APP
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 frontend --status done
```

（`adb exec-out screencap -p` 把 Emulator 当前屏幕截成 PNG 输出到 stdout；先确保 Emulator 已启动且 App 已 `installDebug` 并拉起。`$PF_DIR` 即项目 `.productflow/` 绝对路径。）

**Desktop 分支截图**：对运行中的桌面窗口截图——优先用 Playwright 截 webview（headless/headed 均可），或用系统截图（macOS `screencapture`）；存入 `artifacts/phase-6/` 并登记。**逐页截、一页不漏**（桌面应用复用 ④ Web 前端，平台记 `PC`）：

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
screencapture -x "$PF_DIR/artifacts/phase-6/preview-home-desktop.png"
screencapture -x "$PF_DIR/artifacts/phase-6/preview-detail-desktop.png"

# 桌面应用复用 ④ 的 Web 前端，平台记 PC；逐页截、一页不漏（首页 pg-home、详情页 pg-detail，其余照此循环）
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-home-desktop.png --title "首页（Desktop 实现）" --page-id pg-home --platform PC
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-detail-desktop.png --title "详情页（Desktop 实现）" --page-id pg-detail --platform PC
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 frontend --status done
```

（先确保 `cargo tauri dev` 或 `npm run start` 已起、桌面窗口已显示；`$PF_DIR` 即项目 `.productflow/` 绝对路径。远端/无 GUI 环境跳过截图弹窗，只 reply 告知用户本地自行打开并截图。）

这些截图登记后，用户能在操作台⑥看到「④ 设计稿 ↔ ⑥ 实现截图」按页并排，并**点开实现图圈选**有问题的区域并写意见。这类反馈通过 inbox 的 `type:"preview-feedback"` 进来，正文形如「成品预览反馈 @ 标题（文件），N 处：1. 区域(左25% 上30% 宽40% 高25%)：这里按钮太小…」——`pf_state inbox` 即可读到。检查点读到时**逐条按区域定位修复**（区域坐标是相对截图的百分比，可映射回对应页面元素）后 `reply` 回应，别忽略。

## 测试（无后端项目）

- **涉后端项目**：本阶段只做前端；**单元测试 + 集成测试在 ⑦ 后端实现·测试阶段做**（那时前后端都在、能测端到端）。本阶段做完 `frontend` 即进入检查点，不在本阶段测。
- **无后端项目**（纯静态 / 纯前端，DEC-5 判无后端）：⑦ 阶段隐藏，⑤ DEC-5 已给本阶段补了 `unit-test`（单元测试）· `integration-test`（集成测试）两步——前端做完接着做这两步。集成测试（e2e / Playwright）**确保前端功能端到端完整跑通、没问题**，不是走过场。四类门禁、E2E 用户旅程三处固定来源、数据持久化验证、回归锁、test-report 门禁等具体测试纪律与 ⑦ 的「测试」章节一致，回读 `phase-7-backend.md`「Step 2: 测试」即可，不重复。两步做完（各自真跑绿）：

  ```bash
  python3 "$SKILL_DIR/scripts/pf_state.py" step 6 unit-test --status done
  python3 "$SKILL_DIR/scripts/pf_state.py" step 6 integration-test --status done
  python3 "$SKILL_DIR/scripts/pf_state.py" log "无后端项目：前端单元 + 集成测试全绿（e2e 端到端跑通、回归锁就位）"
  ```

## 检查点（阶段收尾，顺序执行）

1. 读网页端消息并逐条回应（有改动要求就先处理再收尾）：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" inbox
   python3 "$SKILL_DIR/scripts/pf_state.py" reply "<对该条留言的回应>"   # 每条留言各回一次
   ```

2. 写本阶段汇总 `artifacts/phase-6/build-summary.md`（一页：技术栈与目录结构、已实现清单【Web=页面清单 / iOS=屏清单 / Android=屏清单 / Desktop=窗口/屏清单】、（无后端项目）测试结果摘要、已知限制），并登记：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/build-summary.md --title "Phase 6 实现汇总"
   ```

3. 确认本阶段各 step（scaffold + frontend；**无后端项目**另加 unit-test + integration-test）均为 done、预览截图（**按 ④ 页面清单逐页 × 每个选定平台，每张带 `--page-id`/`--platform`，一页不漏**）+ build-summary.md 均已登记。

   **⚠️ 标 phase 6 done 前先跑「实现覆盖校验」（硬闸，绕不过）**——`phase 6 --status done` 会自动校验 ④ 每个有设计稿的「页×平台」是否都有带 `page-id` 的实现截图，缺页会**拒绝标 done**。先自己跑一遍看缺哪些：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_PROJECT" impl-check   # 列 ✅已实现 / ❌缺实现 / ⏭已豁免
   ```

   - **有 ❌ 缺实现**：**首选把那几页补做出来**（把该页跑起来、截图、`artifact 6 <图> --page-id <id> --platform <PC|H5|APP>` 登记）。目标是**每一张 ④ 设计图都真开发出来**。
   - **只有当你判断某页本阶段确实不该做**（如 waitlist 期还没有真实登录/账号体系）——**你无权自行跳过，必须先请示用户批准**（跟 ⑤ 选模板 / ⑧ 选部署目标同理，用 `choice` 抛给用户点选）：
     ```bash
     # 1) 请示用户，阻塞等其点选（choice wait 到时才返回）：
     python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_PROJECT" choice ask --stage 6 \
       --question "「<页名>」本阶段建议不实现（理由：<一句理由>），是否同意跳过？" \
       --option "同意跳过" --option "否，必须实现"      # 输出 ch-xxxx
     python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_PROJECT" choice wait <ch-xxxx> --timeout 600
     # 2) 仅当用户点「同意跳过」才登记豁免；点「否」= 必须把这页做出来，不许豁免：
     python3 "$SKILL_DIR/scripts/pf_state.py" --dir "$PF_PROJECT" page set <pg-id> --impl-skip "<理由>（用户已确认）"
     ```
     **禁止在没问用户的情况下自行 `--impl-skip`**——豁免权在用户、不在你。每页要么真做出来、要么用户点头同意跳过；超时（用户没点）就当作"未批准"，继续尝试实现或在 reply 里说明卡点，别擅自豁免。豁免后在 reply 里列明哪些页未实现及原因。
   - `impl-check` 通过（缺=0）后再标 done：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" phase 6 --status done
   python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 6 前端实现完成：脚手架 + 前端就绪（无后端项目含单元 + 集成测试），待用户确认进入下一阶段"
   ```

4. 在 CLI 向用户汇报：成品预览截图位置、（无后端项目）测试通过情况、已知限制，请用户在网页或 CLI 确认后——**涉后端项目**进入 ⑦ 后端实现·测试（见 phase-7-backend.md），**无后端项目**直接进入 Phase 8 部署（见 phase-8-deploy.md）。用户此前明确说过"全自动"则不停留，直接进入下一阶段。
