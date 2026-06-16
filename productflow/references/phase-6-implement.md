# Phase 6：开发实现

何时读本文件：Phase 5 已 done、用户确认进入开发阶段时。本阶段把设计稿和数据设计变成可运行、测过、有文档的产品代码。

## 输入（开工前确认齐全）

- `artifacts/phase-4/direction.md` —— 最终设计方向（色板/字体/区块顺序），前端唯一依据
- `artifacts/phase-5/template-choice.md` —— 选定的工程模板
- `artifacts/phase-5/schema.sql` —— 建库 DDL
- `artifacts/phase-5/api.md` —— 接口契约
- templates.md —— 各模板的目录结构基准

任一缺失，回到对应阶段补齐再开工，不要凭记忆脑补设计或接口。

阶段开始：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 6 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 6 开发实现开始"
```

## 全阶段纪律（贯穿每一步）

- **动手前**：调用 test-driven-development skill。关键 API 端点和表单提交路径先写测试（红），再写实现（绿）。落地页不必给每个静态区块写测试，测"会坏且坏了有后果"的部分：表单校验、API 返回、数据写入。
- **说"完成"前**：调用 verification-before-completion skill。所有测试真正跑过、截图真正生成，才更新 step 为 done。没跑过的东西不登记。
- **出 bug**：调用 systematic-debugging skill，先复现、定位根因，再修。禁止盲改重试。

## Step 1: scaffold —— 脚手架

按 template-choice.md 选定的模板搭工程，目录结构严格以 templates.md 中该模板的定义为准，不要自创结构（后续阶段和部署脚本依赖这个结构）。

**产品代码放项目根目录**。`.productflow/` 只放过程产物（截图、报告、状态），不放任何会被部署或 git 管理的产品代码——部署和版本管理都针对项目根。

完成标志：依赖装好、dev server 能起、空页面能访问。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 scaffold --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "脚手架完成，dev server 可启动"
```

## Step 2: frontend —— 前端实现

严格按 direction.md 落地：色板色值逐个对、字体与字号层级照搬、区块顺序不增不减不调换。direction.md 是 Phase 4 用户确认过的结论，临场"优化"等于推翻用户决定；确有实现障碍（如字体无法商用），在 CLI 说明并征求意见。

按页面类型选 skill，不要混用：

- 落地页 / 营销页 → `design-taste-frontend`
- 产品 UI（dashboard / 表单页 / admin）→ `frontend-design` 或 `ui-ux-pro-max`（design-taste-frontend 自身声明产品 UI out of scope）

**落地页交付质量底线**（dogfood 实测：三个生成项目都漏了下面这几项，逐条过一遍再标 done）：
- **移动端导航可用**：导航不能在窄屏直接 `display:none` 就完事——给汉堡菜单/可达的区块跳转（带 `aria-expanded`/`aria-controls`），并在 E2E 加一个移动视口（如 390×844）旅程断言导航可达。
- **SEO / 社交分享 meta**：`title`+`description` 之外补 `canonical`、`og:title/og:description/og:image`、`twitter:card=summary_large_image`、`theme-color`；营销页缺 og:image 会让分享卡片没图。favicon 也要有。
- **a11y 基线**：`<main>` landmark + skip-link、表单控件有 `<label>`、可折叠/动态区用 `aria-expanded`/`aria-live`、加 `@media (prefers-reduced-motion: reduce)` 关掉强制动画。
- **没有占位/死链**：CTA、文档、社交链接不能指向 `https://github.com` 这类裸占位或编造的数据（如假 star 数）——要么真实地址，要么"即将上线"页；可在 E2E 加一条断言无裸占位 href。

完成后对运行中的页面截图（桌面端约 1440px 宽、移动端约 390px 宽，截全页），存入 `artifacts/phase-6/`（相对 `.productflow/`）并登记——操作台靠这两张图向用户展示成品。**浏览器工具**：操作台触发的是 headless 后台 agent，没有浏览器 MCP——截图和 E2E 直接用本机已装的 **Python Playwright（chromium headless）** 写脚本（或 webapp-testing / playwright-cli skill），别去 ToolSearch 找 MCP：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-desktop.png --title "成品预览（桌面端）"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/preview-mobile.png --title "成品预览（移动端）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 frontend --status done
```

这两张截图登记后，用户能在操作台⑥**点开圈选**有问题的区域并写意见。这类反馈通过 inbox 的 `type:"preview-feedback"` 进来，正文形如「成品预览反馈 @ 标题（文件），N 处：1. 区域(左25% 上30% 宽40% 高25%)：这里按钮太小…」——`pf_state inbox` 即可读到。检查点读到时**逐条按区域定位修复**（区域坐标是相对截图的百分比，可映射回对应页面元素）后 `reply` 回应，别忽略。

## Step 3: backend —— 后端实现

1. 用 schema.sql 建库（SQLite 系：T2 为 D1、T3 为 better-sqlite3，以 template-choice.md 为准），不要在建库时顺手改表结构；发现 DDL 有问题，先更新 Phase 5 的 schema.sql 再执行，保持单一事实来源。
2. 按 api.md 逐个实现端点。实现与契约出现偏差时，以实际实现为准并在 Step 5 同步回文档。
3. 表单端点必须有**服务端校验**（必填、格式、长度），不能只靠前端。
4. 基础防滥用：honeypot 隐藏字段 **或** 简单频率限制，二选一即可。落地页表单不上验证码、不接风控服务——不过度设计。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 backend --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "后端端点实现完成，服务端校验与防滥用就位"
```

## Step 4: testing —— 测试

两层测试，全部真实跑过：

- **API 测试**：每个端点至少覆盖成功路径 + 一个校验失败路径（如必填缺失返回 4xx）。
- **E2E 用户旅程测试**（@playwright/test，落为项目内可复跑的测试文件如 `tests/e2e/journeys.spec.*` + `npm run test:e2e`——**临时截图脚本不算测试**，它跑完就消失，下个 bug 照样漏网）。**非 Node 项目（T1 纯静态没有 npm 工具链）**用 **Python Playwright（`from playwright.sync_api import sync_playwright`，chromium headless）** 落成等价的可复跑文件 `tests/e2e/test_journeys.py`（自起本地 HTTP server / BASE_URL 可指向容器，作用与 @playwright/test 完全一样：固定、可复跑、跑在真实产物上）——别因为没 Node 就退回一次性脚本。旅程清单的来源固定三处：
  1. **auth/会话全循环**：注册 → 进入 → 退出 → 登录 → 再进入（历史教训：只测注册不测"退出再登录"，曾让"退出后停在注册 tab"的 bug 直接漏到用户手上）；
  2. **core-analysis.mm.md 的傻瓜式路径**逐步走通——那是产品对用户的核心承诺，承诺本身必须有测试锁住；
  3. **每个表单/弹窗的失败路径**：错误提示必须"可见"（断言 toBeVisible 而非仅存在——hidden 属性被 CSS display 顶掉是真实发生过的事故）。
  修过的每个 bug 加一条回归锁用例，注释里写明历史事故。

E2E 必须跑在**真实最终产物**上（容器或构建产物，BASE_URL 可配置），不是 dev server——单元测试用 fake 适配器和内存库没问题，但旅程测试的意义就是验证拼装后的真品。共享实例的旅程测试用 `workers: 1` 串行，避免互踩和触发限流。

- **数据持久化验证**（凡有数据库的项目必做）：在真实部署形态上「写一条 → 重启服务/容器 → 读回来」，确认数据真落盘。内存库和单进程生命周期内的测试都测不出持久化问题——历史事故：SQLite 的 **WAL 日志模式在 Docker Desktop(macOS) 的 bind mount 上写入不落盘**（虚拟文件系统不支持 WAL 的共享内存 mmap），注册"成功"但重启即丢、跨连接查不到。修复是 `journal_mode = DELETE`，并加一条「重开连接后数据仍在」的回归测试锁住。选 SQLite + 容器 + bind mount 时尤其要测这一项。

- **验收纪律**：自查/验收一律跑仓库里的正式测试套件（`npm test` + `npm run test:e2e`），**不要现场手写一次性脚本来"走一遍看看"**——临时脚本会凭记忆猜元素 id/选择器（猜错就是假失败，浪费来回），且跑完即弃、下个 bug 照漏。要覆盖新交互就扩充正式套件：动笔前先 `grep` DOM 确认真实的 id/role，再写进 spec。

把测试命令写进项目根目录 README（如 `npm test`、`npm run test:e2e`），让任何人不读代码就能复跑。

**测试小结产物（门禁，必做）**：把这次测试情况写成 `artifacts/phase-6/test-report.md` 并登记——对**四类测试逐一表态**：① 单元 ② 接口集成 ③ 端到端(E2E) ④ 核心功能回归。每类要么「✅ 通过（写清测了什么、几条、复跑命令）」，要么「N/A（一句理由，如 T1 纯静态无后端 → 单元/接口集成 N/A）」。**不允许某类既不做、也不声明 N/A**——静默跳过测试是这条流水线最容易漏的坑。这份 test-report 会显示在操作台，是「测试做没做、做到什么程度」**唯一可审计的凭证**（流水线不靠 agent 一句口头"测过了"放行）。

测试全绿、且 test-report 四类都已表态后：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/test-report.md --title "测试小结（单元/集成/E2E/回归）"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 testing --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "测试全绿：E2E N/N 通过、回归锁就位（详见 test-report）"
```

测试不过、或四类测试有任一类既没做又没声明 N/A，不许进入下一步——这是 verification-before-completion 的硬约束。**回归测试不是可选项**：E2E 套件必须是项目内固定可复跑的文件（不是跑完即弃的临时脚本），修过的每个 bug 都加一条回归锁。

## Step 5: api-docs —— 文档

1. **`docs/api.md`**（项目根目录下）：按**实际实现**同步 Phase 5 的 api.md——端点、参数、状态码、错误格式，每个端点附一条可直接执行的 curl 示例。文档与实现不符比没有文档更糟。
2. **README**：补全三件事——本地运行步骤、测试命令、部署入口（指向 Phase 7，写"见 .productflow 流水线 Phase 7"即可，不展开）。
3. 把 docs/api.md 复制为过程产物并登记，操作台展示接口文档：

```bash
cp docs/api.md .productflow/artifacts/phase-6/api-docs.md
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/api-docs.md --title "API 接口文档"
python3 "$SKILL_DIR/scripts/pf_state.py" step 6 api-docs --status done
```

## 检查点（阶段收尾，顺序执行）

1. 读网页端消息并逐条回应（有改动要求就先处理再收尾）：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" inbox
   python3 "$SKILL_DIR/scripts/pf_state.py" reply "<对该条留言的回应>"   # 每条留言各回一次
   ```

2. 写本阶段汇总 `artifacts/phase-6/build-summary.md`（一页：技术栈与目录结构、已实现端点清单、测试结果摘要、已知限制），并登记：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" artifact 6 artifacts/phase-6/build-summary.md --title "Phase 6 实现汇总"
   ```

3. 确认 5 个 step 均为 done、两张预览截图 + api-docs.md + build-summary.md 均已登记，然后：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" phase 6 --status done
   python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 6 完成：实现+测试+文档就绪，待用户确认进入部署"
   ```

4. 在 CLI 向用户汇报：成品预览截图位置、测试通过情况、API 文档位置，请用户在网页或 CLI 确认后进入 Phase 7 部署（见 phase-7-deploy.md）。用户此前明确说过"全自动"则不停留，直接进入 Phase 7。
