# Phase 2 — 找参考

进入 Phase 2（找参考）时读本文件：本阶段的目标是**带着 Phase 1 沉淀出的风格方向，去多个来源（Dribbble 概念稿 + 落地页/网页画廊真实整页截图）找一组参考供用户挑选**。挑中的参考（`selectedRefs`）是 Phase 3 首图设计的唯一视觉起点——这一步选准了，下游生图才不跑偏。

本阶段只负责"找 + 挑参考"，不生成首图（那是 Phase 3），更不写页面设计方向（那是 Phase 4）。产物全部落在 `artifacts/phase-2/refs/`。

## 前置条件

- Phase 1 已 done，`artifacts/phase-1/replicate-notes.md`（复刻要点）存在。
- 若缺失，回到 phase-1-research.md 补齐再开始——没有调研结论，"风格方向"就是空中楼阁，找参考会乱抓。

## 阶段启动

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 2 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 2 started: finding visual references (multi-source)"
```

## Step 1: style-direction — 确定风格方向

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 2 style-direction --status active
```

先跑 `inbox` 看用户在网页端有没有表达偏好，再从 `replicate-notes.md` 提炼一个**可搜索的风格方向**：3-6 个关键词（如「极简 / 冷色玻璃拟态 / 大留白 / 无衬线粗标题 / SaaS hero」）。这些关键词既用于下一步 Dribbble 搜索，也是网页向导里给用户看的"我们要找什么感觉"。

- 用户已说"全自动" → 直接按 replicate-notes.md 收敛出关键词并 log 一句理由。
- 用户犹豫或方向发散 → 列 2-3 组候选风格让用户挑，挑定再继续。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" log "Style direction: 极简 + 冷色玻璃拟态 + 大留白 + 无衬线粗标题"
python3 "$SKILL_DIR/scripts/pf_state.py" step 2 style-direction --status done
```

## Step 2: search-refs — 多来源找参考

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 2 search-refs --status active
```

带着上一步的关键词去**多个来源**（Dribbble 概念稿 + 落地页/网页画廊真实整页截图）搜索、抠图、逐张登记。**用户在操作台发起 search-refs 请求时**走下面「找参考协作」节的流程；**用户直接在 CLI** 时也按同样动作做（跨 ≥3 来源合计取 6-9 张 → `explore add-ref` 登记），只是不用清前端请求槽。

完成后：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 2 search-refs --status done
```

## Step 3: select-refs — 选定参考

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 2 select-refs --status active
```

让用户从登记好的参考里多选几张（操作台向导里勾选，或 CLI 里念清单让用户报编号）。挑选期间多跑 `inbox`，看用户在网页端的勾选与便签。

- 网页向导：用户勾选后 `explore.json` 的 `selectedRefs` 自动记录，跑 `explore show` 即可看到。
- CLI / 全自动：用 `explore select-refs <ref id...>` 写选中（**别手改 explore.json**），id 来自 `explore show` 的 `refs[].id`：
  ```bash
  python3 "$SKILL_DIR/scripts/pf_state.py" explore select-refs ref-a1b2c3 ref-d4e5f6
  ```
  CLI：用户报编号 → 对照 refs 列表换成 id → `select-refs`，并 log 选中理由。全自动：自选与 replicate-notes.md 风格最一致的 2-3 张 → `select-refs` → log 理由。

选定的参考会原样传给 Phase 3 当生图依据，所以这一步要**说清楚为什么选这几张**，不要只留编号。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 2 select-refs --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "Refs selected: 3 张冷色玻璃拟态参考已定，传给 Phase 3 生首图"
```

## Step 4: extract-lock — 萃取视觉 token + 锁定组件库（还原度脊椎起点）

> 还原度方案（专题 A/B）在 ② 的落点：把选中参考图里**最有价值的真实视觉信息**萃取成结构化 token，并锁定各平台组件库——让 ③④⑥ 有精确数值可照、有同款组件可用，而不是靠肉眼猜。此步是 `design-spec` 脊椎的起点。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step-add 2 extract-lock "萃取视觉token + 锁组件库"
python3 "$SKILL_DIR/scripts/pf_state.py" step 2 extract-lock --status active
```

1. **从选中参考图萃取结构化 token**：`Read` 逐张打开 `selectedRefs` 指向的参考图（`explore show` 里 `selectedRefs` 的 id → 对应 `refs[].file`），提取——主色板（几个 hex）、字体气质（无衬线/衬线 + 字重）、间距节奏、圆角/阴影。写成一份 DTCG 骨架的 tokens JSON（**primitive 层只放描述性命名**——✅ `color.blue.500` / `color.slate.900` / `space.4` / `radius.md`，❌ 别把语义词放 primitive：`color.primary` / `color.action` / `color.bg` 是 **semantic 层**的事，③④ 再用 alias `{color.blue.500}` 建语义层，`spec check` 会警告 primitive 里的语义词；**②先不做 semantic**），存 `artifacts/phase-2/tokens-draft.json`，再导入 design-spec：
   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" spec set-tokens --file artifacts/phase-2/tokens-draft.json
   ```
   （这是**草案**——③ 首图定稿后反萃取加精、④ 定稿；此处先给下游一个真实锚点，好过一路模糊文字。）

2. **锁定各平台组件库**（按产品类型 + 平台 + 参考风格）：先按 `wizard.json` 的 `platforms` 和产品类型定候选，再**请用户拍板**（与 ⑤ 选模板 / ⑧ 选部署目标同一套用户拍板机制；**全自动模式跳过、按推荐自动选并 log**）：
   ```bash
   # 非全自动：抛 choice 让用户点选（每个选定平台各一次，或合并问）
   ID=$(python3 "$SKILL_DIR/scripts/pf_state.py" choice ask --stage 2 \
         --question "Web 端组件库建议 shadcn/ui + Tailwind（理由：<产品类型> + 参考风格<…>），采用？" \
         --option "采用 shadcn/ui + Tailwind" --option "改用 Ant Design" --option "改用 MUI")
   python3 "$SKILL_DIR/scripts/pf_state.py" choice wait "$ID" --timeout 600   # 解析 stdout JSON 判超时
   ```
   **默认推荐**（可按参考风格调）：Web/桌面 = `shadcn/ui + tailwind`；iOS = SwiftUI 系统组件 + HIG（不引三方）；Android = Material 3 Compose。用户点定（或全自动）后锁进 design-spec（每个选定平台各一条）：
   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" spec set-lib --platform PC --lib "shadcn/ui + tailwind" --theme neutral --catalog artifacts/phase-2/component-catalog.md
   ```

3. **生成组件目录**：按 `references/component-catalog-template.md` 的格式，对选定库列出本项目会用到的组件（按预期页面裁剪，不必全库照搬），写 `artifacts/phase-2/component-catalog.md`——这是 ④⑥「用哪个组件」的单一事实来源。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 2 extract-lock --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "已萃取视觉 token 草案 + 锁定组件库 + 生成组件目录（还原度脊椎起点）"
```

> **降级**：某平台无成熟组件库生态时，回退「token + direction 文字」手写，log 说明、不 block（专题 B6）。

## 找参考协作

用户在操作台走到「找参考」步时，会在网页上请求 Agent 协作。请求出现在 `inbox`（`type: "explore-request"`），同时 `.productflow/explore.json` 的 `request` 字段按 kind 分槽记录——本阶段对应 `search-refs` 槽。**会话里每个检查点都顺手 `$PF inbox`，看到 `search-refs` 请求就处理**：

```bash
PF="python3 $SKILL_DIR/scripts/pf_state.py"   # 已 export PF_PROJECT
$PF explore show      # 看 request（含 search-refs 槽）、用户风格偏好(stylePrefs)、已登记的 refs
```

**请求 `search-refs`（多来源找参考）**，按序执行：

1. **关键词来自市场调研、按产品类型找界面**（不是凭空、更不是一律找落地页）：先读 `artifacts/phase-1/replicate-notes.md`（风格方向候选 + 推荐信息架构）、`artifacts/phase-1/positioning.md` 与 `brief.json`（产品类型/定位/目标用户）、`artifacts/phase-1/competitors.md`（竞品风格，若有），**判断这是什么产品、核心界面是什么**（工具→看板/列表/详情；数据→仪表盘；社交→feed/资料页；电商→商品/结算；纯落地页类→营销首页），据此 +`request.keywords`（用户额外风格标签）合成搜索词。**落地页只是产品里最简单的一类——做 App / Web 应用就找它的产品界面 UI，别一律搜 landing page。**
   - **先呈现关键词、再搜**：把本轮关键词清单 + 一句话依据写出来（前端会先显示给用户再开搜）：`$PF explore set-search-plan --keyword <词1> --keyword <词2> --basis "<依据，如：SaaS 工具型 + 冷色玻璃拟态(调研风格候选A) + 桌面应用界面>"`
   - **产品类型 + 平台一起定词**：读 `wizard.json` 的 `platforms`/`primary`（缺失就从 `brief.json`/定位推断或问用户，**别因 wizard.json 缺失就卡住**）。按产品类型搜真实界面：工具/SaaS→`<品类> dashboard / web app UI / app UI`、社交→`social app UI`、电商→`ecommerce UI`、内容→`<品类> app UI`，**确实是纯落地页/官网**才搜 `landing page`。移动端搜 mobile app UI、桌面端搜 web app/dashboard UI，**别给 App/Web 应用只找营销落地页**；多平台优先 primary，必要时各端都找几张并 title 标「(PC)/(移动)」。
   - **APP 项目优先用真实参考**：Phase 1 若已抓了商店官方截图（`artifacts/phase-1/appstore/`，见 phase-1-research.md），那是**真实 App 界面**，比 Dribbble 设计稿更直观——可直接 `explore add-ref artifacts/phase-1/appstore/<...>.png --title "<App名> 真实界面"` 登记进来供用户挑，和 Dribbble mockup 互补（别只靠 mockup）。用户也可直接给你参考图。
   - **零输入**（`keywords` 空）：用户没给方向——先读 `brief.json` 理解产品定位/目标用户，自己推断 2-3 个贴切关键词再搜，别空手搜。
   - **精炼轮**（`request.seedRef` 有值，即用户点了某张参考的「＋ 类似」）：先 `Read` 打开种子图 `seedRef.file` 看清它的视觉风格，再据此 + 产品定位搜「更多同一风格」的，不要再找跑偏方向。可多轮累积。
   - **去重·翻新轮（第二/三次找）**：找参考可能多轮累积。开搜前先 `explore show` 看 `refs[].source`（已登记的来源），**本轮绝不重复下载/登记这些**。要拿到新结果：① 对应来源**翻页/换分类**（Dribbble 加 `?page=2`、`?page=3`；画廊类翻下一页/换分类）或**换/扩关键词**、**换个来源**；② 一次多收 15-20 个候选，**先过滤掉已有来源 URL（及明显同图）**，再从剩下的取 6-9 张新的——别只取第 1 页前几个（那就是上轮抓过的）。`explore add-ref` 对同来源/同文件也有兜底去重（重复会被跳过、不报错）。
2. **多来源找（别再单一 Dribbble；一次从 ≥3 个不同来源分配 6-9 张名额）**：
   - 『视觉概念稿』**Dribbble**：`dribbble.com/search/<关键词>`（关键词 `-` 连接或 URL 编码）→ 点进 `/shots/` 详情页取主图 `cdn.dribbble.com` 高清原图。
   - 『真实整页截图』落地页/网页画廊——**卡片预览图本身就是真实上线网站的整页截图**，直接取卡片/详情页里尺寸最大的预览图 URL 下载（不是 og:image、无需再点进设计稿），版式最接近成品：
     - A1 落地页画廊：One Page Love `onepagelove.com`、Landing.love `www.landing.love`、Lapa Ninja `www.lapa.ninja`、Land-book `land-book.com`
     - A2 高端网页/动效：Awwwards `www.awwwards.com/websites/`、SiteInspire `www.siteinspire.com`、Framer Gallery `www.framer.com/community/gallery/`
   - **分配原则**：落地页/官网/Web 应用→多取 A1/A2 真实整页截图 + 少量 Dribbble 概念稿；原生 App→以 Dribbble + 商店真实截图为主，A1/A2 取几张补 Web/营销风格。任何情况下都别只压一个来源。
   - **浏览器优先用 camoufox**（反检测 Firefox，画廊/Dribbble 更不易被挡）：若 `python3 -c "import camoufox"` 能导入，用 `from camoufox.sync_api import Camoufox`（`with Camoufox(headless=True) as b: page=b.new_page()`，API 同 Playwright Page）；导入失败再退回本机 **Python Playwright（chromium headless）**。headless 后台 agent **没有浏览器 MCP**（别去 ToolSearch 找 MCP）；交互式 CLI 有浏览器可正常用。⚠️ Land-book / Lapa Ninja / SiteInspire 有 Cloudflare/限流，**必须走真浏览器**，裸 curl 会 403/429。
3. 跨来源合计取 6-9 张（覆盖不同风格倾向，给对比空间），存进 `artifacts/phase-2/refs/<n>.png`（先 `mkdir -p`）：Dribbble 点进详情页取主图 `cdn.dribbble.com` 高清 URL；画廊类直接取卡片/详情页**最大预览整页截图** URL；都用 curl/playwright 下载真实原图。
   - **不要用浏览器截图兜底**：某来源取不到真实图就换下一个来源/跳过（宁可少几张，不存模糊截图/空白图）；**所有来源整体都访问失败、一张真图都没拿到**才**不要 done-request**、不登记任何东西，直接结束并明确说「访问失败」——前端会提示用户重试。
4. 逐张登记，每张一句话描述 + 来源用**作品详情页 URL**（用户可点开看原帖）：

```bash
mkdir -p artifacts/phase-2/refs
$PF explore add-ref artifacts/phase-2/refs/1.png --title "<一句话风格亮点>" --source "<dribbble URL>" --desc "<用 Read 打开这张图后写：风格/品类/含哪些界面区块，如 '深色看板式任务管理 App，列表+卡片+详情抽屉'>"
# 用户也可在网页直接「粘贴 / 拖入图片」手动加参考（人工注入品味，带 desc『用户手动添加』）——你检查点能在 refs 里看到，当作用户给的方向。
# …每张一条…
```

5. 全部登记完，清掉自己这一槽的请求（带 `--kind`，不动 Phase 3 的 `gen-heroes` 槽）：

```bash
$PF explore done-request --kind search-refs    # 网页轮询到该槽清空即知完成，参考自动出现在向导里供用户多选
```

**请求 `collect-ref`（用户贴了一个参考链接）**：目标是拿到**链接里那张设计图本身**，不是网页截图。按优先级：① 链接本身是图片（扩展名/content-type 为 image）→ 直接下载；② 作品/设计页（Dribbble、Behance、Mobbin、Pinterest 等）→ Playwright 打开后读 `<meta property="og:image">`（取不到再试 `twitter:image` 或正文最大 `<img>`），那是高清原图 URL（Dribbble 多为 `cdn.dribbble.com/...`），下载这张图，**别截网页**；③ 仅当是普通网站、抠不到主视觉图（如想参考整页排版的落地页）才整页截图兜底。下完 `explore add-ref ... --source "<原链接>"`，再 `done-request --kind collect-ref`。

版权红线同 Phase 1：参考只供风格判断、给用户挑感觉用，**不抄袭、不盗图、不进最终产品**。

## 检查点

阶段结束依次执行，顺序不可乱（先读消息再关阶段，避免漏掉用户在网页端的最后意见）：

1. `python3 "$SKILL_DIR/scripts/pf_state.py" inbox` 读网页端消息，逐条 `python3 "$SKILL_DIR/scripts/pf_state.py" reply "<回应>"`；涉及参考增删/重选的，先落实到 `explore`（`add-ref` 或确认 `selectedRefs`）再继续。
2. **完成标准 = 选了参考**：本阶段没有「产物画廊」产物（参考存在 explore 里、在找参考面板展示，不进 state 的 artifacts）。所以判定完成只看一条——`explore show` 的 **`selectedRefs` 非空**（用户已选定至少一张参考）。`selectedRefs` 为空就别标 done，先等用户选/提示去选。
3. `python3 "$SKILL_DIR/scripts/pf_state.py" phase 2 --status done`
4. `python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 2 done: references found and selected"`
5. CLI 向用户汇报：找了几张参考、选中哪几张及理由、它们的共同风格倾向；请用户确认后进入 Phase 3 首图设计（见 phase-3-hero.md）。用户已明确"全自动"则不停留。
