# Phase 6：开发实现

何时读本文件：Phase 5 已 done、用户确认进入开发阶段时。本阶段把设计稿和数据设计变成可运行、测过、有文档的产品代码。

## 输入（开工前确认齐全）

- `artifacts/phase-4/direction.md` —— 最终设计方向（色板/字体/区块顺序），前端唯一依据
- `artifacts/phase-5/template-choice.md` —— 选定的预设（含平台与栈），决定本阶段走 Web 还是 iOS 分支
- templates.md —— 各预设的目录结构基准与各阶段衔接

平台相关产物（按 template-choice.md 的预设取其一）：

- **Web 预设（primary = PC / H5，T1/T2/T3）**：`artifacts/phase-5/schema.sql`（建库 DDL，T1 纯静态则 skipped）+ `artifacts/phase-5/api.md`（接口契约）。
- **iOS 预设（primary = APP，P-iOS）**：`artifacts/phase-5/models.swift`（从同批实体推导的 SwiftData `@Model` 数据层，替代 schema.sql）；纯本地 App 无网络 API，schema-ddl 与 api-contract 两步已在 Phase 5 标 skipped，本阶段无 api.md。

任一该有的缺失，回到对应阶段补齐再开工，不要凭记忆脑补设计、数据层或接口。

**先认清平台分支**：读 template-choice.md 里登记的平台与预设——`PC/H5` 走下文 Web 流程（Node/Playwright），`APP`（本期即 iOS）走各步里标注的 **iOS 分支**（Xcode/SwiftUI/SwiftData，测试用 XCTest/XCUITest 在 Simulator 跑）。下面每个 step 先给 Web 主线，再给 iOS 分支，不要混用两条工具链。

阶段开始：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 6 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 6 开发实现开始"
```

## 全阶段纪律（贯穿每一步）

- **动手前**：调用 test-driven-development skill。关键路径先写测试（红），再写实现（绿）。Web 测关键 API 端点和表单提交；iOS 测模型/持久化逻辑与核心交互旅程。落地页/纯展示页不必给每个静态区块写测试，测"会坏且坏了有后果"的部分：表单校验、API 返回、数据写入（iOS 对应：写入查重、SwiftData 持久化、关键视图状态）。
- **说"完成"前**：调用 verification-before-completion skill。所有测试真正跑过（Web `npm run test:e2e`；iOS `xcodebuild test`）、截图真正生成，才更新 step 为 done。没跑过的东西不登记。
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

⚠️ **仅当 agent 在能访问用户桌面 GUI 的本机会话时才弹窗**（本机 macOS 从用户终端起的 server 通常可以）。跑在远端/无显示环境（Ubuntu/root 服务器、无 `DISPLAY` 的后台进程）时 `open` / `xdg-open` / `open -a Simulator` 会失败——这种情况**跳过弹窗**，改为只用 `reply` 把 `http://localhost:$PORT` 告诉用户让其自行打开（或 `ssh -L` 端口转发），**别让 open 失败把流水线带成 command error**（同 iOS 缺 Xcode 时"停下说明、别硬跑"的防御姿态）。

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

## ultracode 实现模式（本阶段构建首选）

本阶段开发实现**优先用 ultracode（Workflow 多代理编排）**，不要单线程串行把代码从头写到尾：

- **拆任务并行推进**：把构建拆成相互独立、可并行的任务——前端/界面、后端/数据层、各功能模块、测试各自一条线推进，能并行就并行，而不是一个 step 写完再写下一个。模块间有契约依赖（如接口契约、`@Model` 结构）的，以 Phase 5 已定的单一事实来源对齐，避免并行时各写各的对不上。
- **对抗式验证**：实现完不要自说自话"写完了"——用**独立 agent 复核代码 + 真正跑测试**来确认。沿用本阶段「四类测试 + test-report 门禁」，用多代理把覆盖做厚（不同 agent 分别补单元/集成/E2E/回归，比单线程更容易把漏网路径测到）。
- **两条分支都适用**：Web 与 iOS 一样拆并行——iOS 可把 视图（SwiftUI）/数据层（SwiftData `@Model`）/XCTest/XCUITest 拆成并行任务推进。
- **降级**：headless 后台 agent 若拿不到 Workflow 工具（ultracode 不可用），就退到用 Task 子代理 / 单线程把活做扎实——不硬依赖 ultracode，但有就用。下面各 step 的纪律、门禁、命令在两种模式下都不变。

## Step 1: scaffold —— 脚手架

按 template-choice.md 选定的预设搭工程，目录结构严格以 templates.md 中该预设的定义为准，不要自创结构（后续阶段和部署/上架脚本依赖这个结构）。

**产品代码放项目根目录**。`.productflow/` 只放过程产物（截图、报告、状态），不放任何会被部署或 git 管理的产品代码——部署和版本管理都针对项目根。

**Web 分支（T1/T2/T3）**：搭前端目录 + 后端/Worker（按档），装依赖。完成标志：依赖装好、dev server 能起、空页面能访问。

**iOS 分支（P-iOS）**：建 Xcode 工程（SwiftUI App 模板），按 templates.md 的 P-iOS 树搭 `MyApp/`（`MyAppApp.swift` 标 `@main`、挂 `.modelContainer(for:)`）+ `Models/`、`Views/`、可选 `ViewModels/`/`Services/` + `MyAppTests/`（XCTest）+ `MyAppUITests/`（XCUITest），依赖用 **SPM**（不引 CocoaPods）。
- **前置检测**（缺了提示用户装 Xcode / 命令行工具，别硬跑报 command not found）：`xcodebuild -version`、`xcrun simctl list devices`。检测不到 Xcode 时停下，在 CLI 说明"需要装 Xcode 才能继续 iOS 构建"，不要把流水线跑成一串 `command not found`。
- 完成标志：`xcodebuild build` 能编过、空 App 能在 Simulator 起来、`ModelContainer` 挂载成功（一个空 `@Model` 也行）。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 scaffold --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "脚手架完成，dev server 可启动 / iOS 空 App 可在 Simulator 启动（按平台二选一）"
```

## Step 2: frontend —— 前端 / 界面实现

（用 ultracode 时，前端/界面与 Step 3 后端/数据层可并行推进，不必等后端完工再动前端。）

严格按 direction.md 落地：色板色值逐个对、字体与字号层级照搬、区块顺序不增不减不调换。direction.md 是 Phase 4 用户确认过的结论，临场"优化"等于推翻用户决定；确有实现障碍（如字体无法商用），在 CLI 说明并征求意见。

**iOS 分支（P-iOS）**：界面用 **SwiftUI** 视图实现，按 direction.md 的色板/字体/区块顺序落进各 `Views/` 文件（色值用 `Color(hex:)`/资产目录，字体层级照搬到 `.font(...)`）；产品 UI 性质的界面参照下面"产品 UI"那条选 skill。下面的"落地页交付质量底线"是 Web 营销页专属（移动端导航/SEO meta/裸 href 等是 web 概念），iOS App 不适用——iOS 的质量底线在 Step 4 的 XCUITest 旅程与 Simulator 截图里把关。其余 step 2 内容（截图登记、preview-feedback 圈选反馈）iOS 同样适用，见本步末尾的 iOS 截图说明。

按页面类型选 skill，不要混用：

- 落地页 / 营销页 → `design-taste-frontend`
- 产品 UI（dashboard / 表单页 / admin / **iOS App 界面**）→ `frontend-design` 或 `ui-ux-pro-max`（design-taste-frontend 自身声明产品 UI out of scope）

**落地页交付质量底线**（dogfood 实测：三个生成项目都漏了下面这几项，逐条过一遍再标 done）：
- **移动端导航可用**：导航不能在窄屏直接 `display:none` 就完事——给汉堡菜单/可达的区块跳转（带 `aria-expanded`/`aria-controls`），并在 E2E 加一个移动视口（如 390×844）旅程断言导航可达。
- **SEO / 社交分享 meta**：`title`+`description` 之外补 `canonical`、`og:title/og:description/og:image`、`twitter:card=summary_large_image`、`theme-color`；营销页缺 og:image 会让分享卡片没图。favicon 也要有。
- **a11y 基线**：`<main>` landmark + skip-link、表单控件有 `<label>`、可折叠/动态区用 `aria-expanded`/`aria-live`、加 `@media (prefers-reduced-motion: reduce)` 关掉强制动画。
- **没有占位/死链**：CTA、文档、社交链接不能指向 `https://github.com` 这类裸占位或编造的数据（如假 star 数）——要么真实地址，要么"即将上线"页；可在 E2E 加一条断言无裸占位 href。

完成后对运行中的界面截图，存入 `artifacts/phase-6/`（相对 `.productflow/`）并登记——操作台靠这些图向用户展示成品。

**⚠️ 视觉还原比对（前端门禁，最容易被跳过、直接决定"前端效果行不行"）**：实现的界面**不是写完截个图就算 done**——必须对着设计稿**一一比对、迭代到位**，否则还原效果差：

1. 把实现的界面截图（同视口/同尺寸：Web 桌面 ~1440 / 移动 ~390；iOS 用对应机型 Simulator）。
2. **并排比对「实现截图」vs「④ 页面设计稿」**——设计稿在 `artifacts/phase-4/`（对应该页该平台的稿；首页/基调可参照 ③ 定稿首图 `artifacts/phase-3/heroes/<定稿>`）。你是**有视觉能力的 Claude**：用 `Read` 同时打开「实现截图」和「设计稿」两张图，**逐项核对并列出每一处差异**——整体布局 / 区块顺序 / 间距与留白 / 配色（逐个 hex 比）/ 字体·字号·字重·行高 / 圆角·阴影 / 组件样式与状态 / 图标 / 图片与占位。
3. **按差异改样式 → 重新截图 → 再比对，迭代到「实现与设计稿高度一致」为止**——不是"差不多就行"：`direction.md` / 设计稿是 Phase 4 用户确认过的合同，颜色、间距、字体必须对得上。**这一步没做，就是用户说的"还原效果差、前端不行"。**
4. **比对对齐后**才标 `frontend --status done`；把"实现截图 + 对应设计稿"一并登记，用户在操作台能对比验收。

> Web、iOS 都要做这一步（iOS 对着 ④ 对应平台稿 + ③ 基调，用 Simulator 截图比对）。圈选反馈（preview-feedback）是用户帮你挑漏的，但**主动一一比对是你的本职**，别等用户圈。

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

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 backend --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "后端端点实现完成，服务端校验与防滥用就位 / iOS 数据层 @Model 就位，写入查重保唯一（按平台二选一）"
```

## Step 4: testing —— 测试

两层测试，全部真实跑过。Web 主线见下；**iOS 分支见本步末尾的"iOS 测试分支"**（XCTest + XCUITest 在 Simulator 跑），四类测试门禁两条分支共用。（用 ultracode 时，让独立 agent 复核代码并把四类测试分头并行做厚，对抗式确认而非自说自话——见上文「ultracode 实现模式」。）调试这层往往是长循环：**按上文「调试期沟通与开调试现场」边调边读 `inbox`、卡在歧义点用 `choice ask`+`wait` 暂停问、并把在跑的产物实时开给用户看**，别把沟通攒到阶段收尾。

- **API 测试**：每个端点至少覆盖成功路径 + 一个校验失败路径（如必填缺失返回 4xx）。
- **E2E 用户旅程测试**（@playwright/test，落为项目内可复跑的测试文件如 `tests/e2e/journeys.spec.*` + `npm run test:e2e`——**临时截图脚本不算测试**，它跑完就消失，下个 bug 照样漏网）。**非 Node 项目（T1 纯静态没有 npm 工具链，或 iOS 项目）**别因为没 Node 就退回一次性脚本——落成等价的可复跑测试文件：Web 纯静态用 **Python Playwright（`from playwright.sync_api import sync_playwright`，chromium headless）** 写 `tests/e2e/test_journeys.py`（自起本地 HTTP server / BASE_URL 可指向容器）；**iOS 用 XCUITest**（见"iOS 测试分支"）。作用与 @playwright/test 一致：固定、可复跑、跑在真实产物上。旅程清单的来源固定三处：
  1. **auth/会话全循环**：注册 → 进入 → 退出 → 登录 → 再进入（历史教训：只测注册不测"退出再登录"，曾让"退出后停在注册 tab"的 bug 直接漏到用户手上）；
  2. **core-analysis.mm.md 的傻瓜式路径**逐步走通——那是产品对用户的核心承诺，承诺本身必须有测试锁住；
  3. **每个表单/弹窗的失败路径**：错误提示必须"可见"（断言 toBeVisible 而非仅存在——hidden 属性被 CSS display 顶掉是真实发生过的事故）。
  修过的每个 bug 加一条回归锁用例，注释里写明历史事故。

E2E 必须跑在**真实最终产物**上（容器或构建产物，BASE_URL 可配置），不是 dev server——单元测试用 fake 适配器和内存库没问题，但旅程测试的意义就是验证拼装后的真品。共享实例的旅程测试用 `workers: 1` 串行，避免互踩和触发限流。

- **数据持久化验证**（凡有持久化的项目必做）：Web 在真实部署形态上「写一条 → 重启服务/容器 → 读回来」，确认数据真落盘。内存库和单进程生命周期内的测试都测不出持久化问题——历史事故：SQLite 的 **WAL 日志模式在 Docker Desktop(macOS) 的 bind mount 上写入不落盘**（虚拟文件系统不支持 WAL 的共享内存 mmap），注册"成功"但重启即丢、跨连接查不到。修复是 `journal_mode = DELETE`，并加一条「重开连接后数据仍在」的回归测试锁住。选 SQLite + 容器 + bind mount 时尤其要测这一项。**iOS 对应项**：SwiftData 持久化往返（写一条 → 重建 `ModelContext`/`ModelContainer` → 读回），见"iOS 测试分支"的②集成。

- **验收纪律**：自查/验收一律跑仓库里的正式测试套件（Web `npm test` + `npm run test:e2e`；iOS `xcodebuild test`），**不要现场手写一次性脚本来"走一遍看看"**——临时脚本会凭记忆猜元素 id/选择器（猜错就是假失败，浪费来回），且跑完即弃、下个 bug 照漏。要覆盖新交互就扩充正式套件：动笔前先确认真实的元素标识（Web `grep` DOM 的 id/role；iOS 用 `accessibilityIdentifier` 标记控件，XCUITest 按 id 取），再写进测试文件。

把测试命令写进项目根目录 README（Web 如 `npm test`、`npm run test:e2e`；iOS 如 `xcodebuild test -scheme MyApp -destination '...'`），让任何人不读代码就能复跑。

### iOS 测试分支（P-iOS）

iOS 没有 Node/Playwright 工具链，测试器是 **iOS Simulator**，命令是 `xcodebuild test`（指定 `-scheme` + `-destination 'platform=iOS Simulator,name=iPhone 15'` 之类）；模拟器开关/重置用 `xcrun simctl`。**前置检测** `xcodebuild -version`、`xcrun simctl list devices`，缺了提示装 Xcode，别硬跑。所有测试落成项目内 `MyAppTests/`（XCTest）/ `MyAppUITests/`（XCUITest）下可复跑的文件——**临时脚本不算测试**，跟 Web 同纪律。四类门禁映射到 iOS：

- **①单元 = XCTest**：模型逻辑、`@Observable` 视图模型、纯函数。每类逻辑至少一条成功路径 + 一条边界/失败路径（如写入查重命中时不重复插入）。
- **②集成 = SwiftData 持久化往返**（凡有持久化必做，对应 Web 的"写→重启→读回"）：在 XCTest 里建**临时** `ModelContainer`（`isStoredInMemoryOnly: false` 指向临时目录，或新建独立 container），「写一条 → 重建 `ModelContext`/`ModelContainer` → 读回」，断言数据仍在、字段一致、唯一性约束生效。内存里写完直接读不算往返——必须跨 context/container 重建才测得出真落盘。
- **③E2E = XCUITest 旅程**：core-analysis.mm.md 的傻瓜式路径在 Simulator 上点通（新建 → 保存 → **杀掉并重开 App 数据仍在** → 编辑 → 删除等核心循环）。控件用 `accessibilityIdentifier` 标记后按 id 取；断言用 `XCTAssert(element.exists)` / `waitForExistence`，别靠屏幕坐标硬点。旅程清单来源同上文三处（会话/状态全循环、核心承诺路径、每个表单弹窗的失败提示可见）。
- **④回归 = 修过的 bug 加 XCUITest 锁**：每个修过的 bug 补一条 XCUITest（或 XCTest，视 bug 层级），注释写明历史事故；跑完即弃的临时脚本不算。

iOS 端的"E2E 跑在真实最终产物上"= 用 **Release 配置**或与上架一致的构建跑 XCUITest，别只测 Debug。

**测试小结产物（门禁，必做）**：把这次测试情况写成 `artifacts/phase-6/test-report.md` 并登记——对**四类测试逐一表态**：① 单元 ② 接口集成 ③ 端到端(E2E) ④ 核心功能回归。每类要么「✅ 通过（写清测了什么、几条、复跑命令）」，要么「N/A（一句理由，如 T1 纯静态无后端 → 单元/接口集成 N/A）」。iOS 四类映射：①=XCTest，②=SwiftData 持久化往返，③=XCUITest 旅程，④=XCUITest 回归锁（iOS 项目这四类一般都该有实测，"无网络 API"不等于免测——②落到持久化往返而非接口）。**不允许某类既不做、也不声明 N/A**——静默跳过测试是这条流水线最容易漏的坑。这份 test-report 会显示在操作台，是「测试做没做、做到什么程度」**唯一可审计的凭证**（流水线不靠 agent 一句口头"测过了"放行）。

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

## 检查点（阶段收尾，顺序执行）

1. 读网页端消息并逐条回应（有改动要求就先处理再收尾）：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" inbox
   python3 "$SKILL_DIR/scripts/pf_state.py" reply "<对该条留言的回应>"   # 每条留言各回一次
   ```

2. 写本阶段汇总 `artifacts/phase-6/build-summary.md`（一页：技术栈与目录结构、已实现清单【Web=端点清单 / iOS=屏与 `@Model` 清单】、测试结果摘要、已知限制），并登记：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/build-summary.md --title "Phase 6 实现汇总"
   ```

3. 确认 5 个 step 均为 done、预览截图（Web 桌面+移动 / iOS 两张代表屏）+ api-docs.md（iOS 为数据模型文档）+ build-summary.md 均已登记，然后：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" phase 6 --status done
   python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 6 完成：实现+测试+文档就绪，待用户确认进入部署"
   ```

4. 在 CLI 向用户汇报：成品预览截图位置、测试通过情况、文档位置（Web=API 文档 / iOS=数据模型文档），请用户在网页或 CLI 确认后进入 Phase 7（Web=部署 CF Pages/Worker/单机；iOS=archive → 上传 TestFlight，提审前停手；见 phase-7-deploy.md）。用户此前明确说过"全自动"则不停留，直接进入 Phase 7。
