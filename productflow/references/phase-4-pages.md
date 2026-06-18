# Phase 4 — 页面设计

进入 Phase ④（页面设计）时读本文件：本阶段用 Phase ③ 定下的**首图视觉基调**，把项目**所有页面**逐一设计出来，并为每个页面产出 **PC / H5 / APP** 各平台版本。最终定稿设计方向 `artifacts/phase-4/direction.md`，作为 Phase ⑤（功能与数据设计）、Phase ⑥（开发实现）的设计输入。

## 前置条件

- Phase ③（首图设计）已 done，首图与视觉基调已定：`artifacts/phase-3/heroes/` 下有选中首图，`explore.json` 的 `selectedHero`/`styleSummary` 记录其风格（配色 hex、字体气质、留白、质感）。
- Phase ① 已 done，`artifacts/phase-1/replicate-notes.md`（复刻要点）存在——其中"推荐信息架构"是本阶段 **page-map** 列页面的依据。
- 若 ③ 缺首图、① 缺复刻要点 → 回对应阶段补齐再开始。没有视觉基调，逐页设计就会各画各的；没有信息架构，列不全页面。

## 阶段启动

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 4 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 4 started: mapping all pages from P1 信息架构 + P3 视觉基调"
```

> 版权红线（贯穿全阶段）：复刻竞品只学布局结构、信息架构、风格思路；不抄文案、不盗图。所有页面的文案、配图必须是本产品自己的。

## Step 1: page-map — 列出项目应有的所有页面（进 P4 第一步就铺占位带）

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 4 page-map --status active
```

**这是进入 P4 的第一件事：把项目应有的全部页面一次性列清，并立即 `page add` 铺成画布顶部的占位带。** 不要边设计边想起来一页加一页——先有完整地图，才知道总量、才能看出哪页还缺。

页面清单从两处推断，二者结合：

1. **Phase ① 的"推荐信息架构"**（`replicate-notes.md`）——它给的是落地页从上到下的区块清单与顺序；据此判断本项目是单落地页，还是多页站点（如官网首页 + 定价页 + 关于页 + 登录/注册 + 文档/帮助 + 法务页等）。
2. **Phase ③ 的视觉基调**——基调偏"营销/品牌"则页面偏内容页；基调暗示有产品功能（如 dashboard 气质的首图）则需补产品 UI 页（登录、控制台、设置）。

为**每一个**推断出的页面跑 `page add`，**必须带 `--note` 写清这一页的依据**（为什么该有这页、放什么内容、信息架构里对应哪段），并按模块用 `--group` 分组：

```bash
PF="python3 $SKILL_DIR/scripts/pf_state.py"   # 已 export PF_PROJECT
$PF page add "首页 / 落地页" --group "营销" --note "P1 信息架构主页：hero→功能→定价→FAQ→CTA，回应核心真问题"
$PF page add "定价页"       --group "营销" --note "P1 竞品共性均有独立 pricing 页；首页 pricing 区块的展开"
$PF page add "登录"         --group "账户" --note "P3 首图含 dashboard 气质，推断有产品功能，需账户入口"
$PF page add "注册"         --group "账户" --note "配合登录，承接 CTA 转化"
# …把所有页面铺完…
$PF page list   # 复核：占位带是否覆盖全部页面
```

- `page add` 默认 `status=placeholder`（占位），画布顶部占位带据此画"待设计"。
- `page-map` 阶段**只 add 占位、不传 `--status`**——让所有页保持 placeholder，体现"已列出、尚未开工"。
- 不确定某页是否需要 → 也先 add 成占位并在 `--note` 标"待定"，列全比漏掉好；真不需要可后续 `page rm`。

向用户念页面总数与分组（全自动则 log 一句"共列 N 页，依据 P1 信息架构 + P3 基调"），确认无遗漏后收尾：

```bash
$PF page list   # 给用户/自己看占位带全貌
python3 "$SKILL_DIR/scripts/pf_state.py" step 4 page-map --status done
```

## Step 2: design-pages — 逐页设计

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 4 design-pages --status active
```

> **操作台两种触发**：①在某页卡片上点空的平台格（PC/H5/APP）→ 单独生成那一页那个平台；②点顶部「**批量生成全部（N 页）**」→ 把所有还没设计的页面**按主平台并发各出一版**（`run-stage` 派一个 agent 跑整批）。
>
> **批量必须并发、不要逐页串行**——openai-image-gen 的 `gen.py` 支持 `--concurrency 20`，且 `--prompt` 可重复。所以批量请求的正确做法是：先把每个占位页的 prompt 一次性写好（每页 = 该页内容 + ③ 视觉基调 + 主平台界面描述 + 纯 UI 约束），然后用**一条 gen.py 命令**把它们一起并发出图：
>
> ```bash
> python3 "$GEN" \
>   --prompt "<页1内容> <主平台界面描述> 纯UI, <③基调>, pure UI, no background scene, no device frame, front view" \
>   --prompt "<页2内容> …" \
>   --prompt "<页N内容> …" \
>   --size <主平台: APP/H5=1080x2340, PC=1440x1080> --concurrency 20 --model gpt-image-2 --out-dir artifacts/phase-4
> ```
>
> 出图完按 `prompts.json` 把每张映射回对应页面，逐个 `page set <pg-id> --add-version <文件> --platform <主平台>` 关联（登记串行无妨，耗时的生图已并发）。**别一页一页 gen.py 串行调用**。

按 page-map 的清单**逐页**设计。开始设计某一页时，先把它从占位翻成"设计中"，让画布占位带亮起该页进度：

```bash
$PF page set <pg-id> --status designing
```

（`<pg-id>` 是 `page add` 返回的 `pg-xxxxxx`，或 `page list` 第一列。）

逐页设计要点：

- **统一基调**：每页都从 Phase ③ 的视觉基调取色板（hex）、字体气质、留白密度、圆角/阴影规则——所有页面看起来像同一个产品，不是各画各的。
- **选对工具**（项目硬规则，选错产模板味界面）：
  - 落地页 / 营销页 / 官网内容页 → 用 `design-taste-frontend`（anti-slop 专用）。
  - 产品 UI（dashboard、列表、表单、设置、admin、数据表格）→ **不要用** design-taste-frontend（它自身声明 out of scope），改用 `frontend-design` 或 `ui-ux-pro-max`。
  - 一个项目内两类页面并存时，分别按页面类型选工具。
- **页面骨架来自 P1**：落地页骨架直接用 `replicate-notes.md` 的区块顺序；功能页骨架按该页职责自定。
- 单页设计产物先落 `artifacts/phase-4/pages/<page>/`（如 HTML/CSS 初稿），下一步 platform-versions 再按平台登记版本。

> 某页设计完、但平台版本要在 Step 3 统一出时，本步可只把该页 `--status designing`，待版本登记后自动转 `done`（见下）。逐页推进，画布占位带实时反映"哪些在设计中、哪些已完成"。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 4 design-pages --status done
```

## Step 3: platform-versions — 每页按平台出版本（PC / H5 / APP）

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 4 platform-versions --status active
```

每个页面要按目标平台分别出版本。范围以 Phase ① `scope` 选定的平台为准（用户勾了 PC/H5/APP 中的哪些就出哪些）。为某页的某平台产出版本文件后，用 `--add-version` + `--platform` 登记：

```bash
$PF page set <pg-id> --add-version artifacts/phase-4/pages/home/home-pc.html  --platform PC
$PF page set <pg-id> --add-version artifacts/phase-4/pages/home/home-h5.html  --platform H5
$PF page set <pg-id> --add-version artifacts/phase-4/pages/home/home-app.html --platform APP
```

**`--platform` 用法（关键）**：

- 取值固定为 `PC` | `H5` | `APP`（大小写不敏感，内部统一大写）。
- `--platform` 必须配合 `--add-version` 使用——它标注"这个版本文件是给哪个平台的"。
- `pages.json` 里每个 page 的 `versions` 是数组，元素为对象 `{file, platform}`；同一页多次 `--add-version --platform` 即可挂多个平台版本，按 `(file, platform)` 去重，重复登记不会叠加。
- 不分平台的通用版本可省略 `--platform`（该版本 `platform` 记为 null），但本阶段目标是平台齐全，**优先按平台登记**。
- 登记任一 version 后，若该页仍是 `placeholder` 会**自动转 `done`**；如需保持设计中可显式再 `--status designing`。三个平台都出齐后按需 `--status done` 收口。

**框选局部重绘（用户在画布上自助改）**：用户可在 ④ 画布点某页设计图的「✏️ 框选局部重绘」，框选要改的区域 + 写一句怎么改 → 操作台调 `gpt-image-2` **只重绘选中区域**（其余像素保留），结果自动 `page set --add-version` 挂成**该页的新版本并存**（原版本不动，可对比/回退）。这条不经过你，但你检查点能在该页版本里看到新增稿——当作用户给的局部修订对待，定稿时按用户取舍保留。

PC / H5 / APP 适配差异（每平台单独成版本，不是一份图凑数；每个版本都是该平台的**纯 UI 设计稿**）：

- **PC**：桌面 web 界面（首屏/关键屏），横向（1440 宽基准），宽屏多列、悬停态、信息密度高；无浏览器窗口框。`--size 1440x1080`。
- **H5**：移动 web 界面，竖屏（~9:19.5），单列、点击区域大、首屏聚焦核心 CTA，导航折叠为汉堡/底部栏；无浏览器地址栏。`--size 1080x2340`。
- **APP**：手机 App 原生界面，竖屏（~9:19.5），状态栏/安全区、底部 Tab、手势返回，卡片化/列表化更彻底；状态栏作为 UI 一部分，不是设备外框。`--size 1080x2340`。

⛔ **纯 UI 硬约束（与 Phase ③ 一致）**：每个平台版本都是**该平台的纯 UI 设计稿本身**——界面铺满画面、正视、edge-to-edge；**禁止**背景环境/使用场景/lifestyle 摄影/设备外框（手机在手、笔记本在桌）/浏览器窗口框/营销 case-study 长页场景模板（**不要**用 `ui-mockups/landing-page-case-study.md` 这类场景模板）。

平台版本可用 design-taste-frontend / frontend-design 直接出响应式多档；用 openai-image-gen 出图时，按上表平台对应的 `--size` 直接生成纯 UI 设计稿，**不要套 UI 样机/场景模板**。

⚠️ **必须用 `--prompt` 模式，不要 `--subject ... --category web-design`**——`--subject`+`--category` 会被 `styles.json` 里 web-design 风格自动追加「browser window / desktop frame / background / mockup」等措辞，把背景和设备框塞回来、与纯 UI 矛盾。把该页功能 + 平台界面描述 + ③ 基调风格 + 所有纯 UI 约束揉成**一条完整 prompt**：

```bash
GEN=<openai-image-gen 的 scripts/gen.py 实际路径>
python3 "$GEN" \
  --prompt "<该页一句话功能> <平台界面描述> 纯 UI 设计稿, <③ 基调风格>, pure UI design, fills the frame edge-to-edge, flat, no background scene, no device frame, no browser chrome, front view" \
  --size <PC=1440x1080 / H5=1080x2340 / APP=1080x2340> \
  --count 1 --model gpt-image-2 --out-dir artifacts/phase-4
```

```bash
$PF page list   # 复核每页 versions 数，确认平台覆盖
python3 "$SKILL_DIR/scripts/pf_state.py" step 4 platform-versions --status done
```

### 页面画布上的「页面 × 平台」矩阵

操作台页面画布把 `pages.json` 渲染成一张矩阵：

- **行 = 页面**（按 `group` 分组），**列 = 平台 PC / H5 / APP**。
- 每个单元格读该页 `versions` 里有没有对应 `platform` 的元素：有 → 显示该平台版本（缩略图/已出），无 → 显示"缺"。
- 一眼能看出：哪些页 PC/H5/APP 三平台齐了、哪些页只出了 PC、哪些平台整列还缺。据此回到 Step 3 补齐缺口，直到矩阵填满（或填满 scope 选定的平台列）。
- 页面 `status`（placeholder/designing/done）驱动占位带颜色，`versions` 的平台分布驱动矩阵单元格——两者配合反映整阶段进度。

## Step 4: finalize-direction — 定稿设计方向

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 4 finalize-direction --status active
```

写 `artifacts/phase-4/direction.md`，必须包含以下**五节**（Phase ⑤ 的功能/数据设计、Phase ⑥ 的前端实现都只读这一份，缺项会让下游瞎猜）：

1. **品牌色板**：primary / secondary / accent / 背景 / 文字，全部 hex（承接 Phase ③ 视觉基调，不另起炉灶）。
2. **字体配对**：标题字体 + 正文字体（具体字体名 + fallback），并注明气质（如 geometric sans + humanist serif）。
3. **区块清单及顺序**：核心页面（落地页/首页）从上到下的 section 列表（如 hero → social proof → features → pricing → FAQ → CTA footer），每块一句话说明目的；多页项目再附各页职责一句话。
4. **组件风格**：按钮/卡片/输入框的圆角、阴影、边框规则；留白密度；图标风格。各平台（PC/H5/APP）的适配规则也在此点明（断点、触控尺寸、底部栏等）。
5. **文案骨架**：主标题、副标题、各区块小标题与 CTA 文案的初稿（自写，不抄竞品）。

另附一行：本阶段共出 N 个页面 × 哪些平台、首图基调来源（`artifacts/phase-3/heroes/<选中>`），便于回溯。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 4 artifacts/phase-4/direction.md --title "Design direction (final)"
python3 "$SKILL_DIR/scripts/pf_state.py" step 4 finalize-direction --status done
```

请用户确认 direction.md（CLI 念要点 + 提示网页端可看全文与「页面 × 平台」矩阵）。用户要改 → 改完重新登记同名 artifact；全自动 → log 定稿理由后直接收尾。

## 检查点

阶段结束依次执行，顺序不可乱（先读消息再关阶段，避免漏掉用户在网页端的最后意见）：

1. `python3 "$SKILL_DIR/scripts/pf_state.py" inbox` 读网页端消息，逐条 `python3 "$SKILL_DIR/scripts/pf_state.py" reply "<回应>"`；涉及页面/平台/设计方向的修改先落实（改 direction.md、补 page version）再继续。
2. 确认本阶段产物全部登记：`direction.md`（必有，已 artifact 登记）；`pages.json` 里每页 `status=done`、`versions` 覆盖 scope 选定的平台（PC/H5/APP），各页设计文件在 `artifacts/phase-4/pages/`。用 `page list` 复核占位带与矩阵无缺口。
3. `python3 "$SKILL_DIR/scripts/pf_state.py" phase 4 --status done`
4. `python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 4 done: N 个页面 × PC/H5/APP 版本完成，设计方向定稿"`
5. CLI 向用户汇报：页面总数与分组、各平台版本完成度（矩阵填满情况）、定稿方向要点（色板/字体/区块数）、在操作台的查看位置；请用户确认后进入 Phase ⑤（见 phase-5-spec.md）。用户已明确"全自动"则不停留。
