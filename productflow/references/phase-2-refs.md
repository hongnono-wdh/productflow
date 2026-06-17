# Phase 2 — 找参考

进入 Phase 2（找参考）时读本文件：本阶段的目标是**带着 Phase 1 沉淀出的风格方向，去 Dribbble 找一组落地页参考供用户挑选**。挑中的参考（`selectedRefs`）是 Phase 3 首图设计的唯一视觉起点——这一步选准了，下游生图才不跑偏。

本阶段只负责"找 + 挑参考"，不生成首图（那是 Phase 3），更不写页面设计方向（那是 Phase 4）。产物全部落在 `artifacts/phase-2/refs/`。

## 前置条件

- Phase 1 已 done，`artifacts/phase-1/replicate-notes.md`（复刻要点）存在。
- 若缺失，回到 phase-1-research.md 补齐再开始——没有调研结论，"风格方向"就是空中楼阁，找参考会乱抓。

## 阶段启动

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 2 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 2 started: finding visual references on Dribbble"
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

## Step 2: search-refs — 去 Dribbble 找参考

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 2 search-refs --status active
```

带着上一步的关键词去 Dribbble 搜索、截图、逐张登记。**用户在操作台发起 search-refs 请求时**走下面「找参考协作」节的流程；**用户直接在 CLI** 时也按同样动作做（搜索 → 截 6-9 张 → `explore add-ref` 登记），只是不用清前端请求槽。

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

## 找参考协作

用户在操作台走到「找参考」步时，会在网页上请求 Agent 协作。请求出现在 `inbox`（`type: "explore-request"`），同时 `.productflow/explore.json` 的 `request` 字段按 kind 分槽记录——本阶段对应 `search-refs` 槽。**会话里每个检查点都顺手 `$PF inbox`，看到 `search-refs` 请求就处理**：

```bash
PF="python3 $SKILL_DIR/scripts/pf_state.py"   # 已 export PF_PROJECT
$PF explore show      # 看 request（含 search-refs 槽）、用户风格偏好(stylePrefs)、已登记的 refs
```

**请求 `search-refs`（去 Dribbble 找参考）**，按序执行：

1. 读 `request.keywords`（用户/上一步的风格关键词）+ `request.product`（产品名 + 需求），合成搜索词。
   - **必须区分设备**：读平台信息——`wizard.json` 的 `platforms` / `primary`（网页「新建项目」创建的项目才有；CLI `init` 的项目没有这个文件，就从 `brief.json`/产品定位推断，或直接问用户主平台，**别因为 wizard.json 缺失就报错卡住**）。PC=桌面 web 落地页、H5=移动 web、APP=App UI。按主平台调整搜索词（桌面搜 `landing page web`、移动搜 `mobile app UI / mobile landing`），别给移动端产品找一堆桌面落地页（反之亦然）；多平台项目优先 primary，必要时各平台都找几张并在 title 标注「(PC)/(移动)」。
   - **APP 项目优先用真实参考**：Phase 1 若已抓了商店官方截图（`artifacts/phase-1/appstore/`，见 phase-1-research.md），那是**真实 App 界面**，比 Dribbble 设计稿更直观——可直接 `explore add-ref artifacts/phase-1/appstore/<...>.png --title "<App名> 真实界面"` 登记进来供用户挑，和 Dribbble mockup 互补（别只靠 mockup）。
   - **零输入**（`keywords` 空）：用户没给方向——先读 `brief.json` 理解产品定位/目标用户，自己推断 2-3 个贴切关键词再搜，别空手搜。
   - **精炼轮**（`request.seedRef` 有值，即用户点了某张参考的「＋ 类似」）：先 `Read` 打开种子图 `seedRef.file` 看清它的视觉风格，再据此 + 产品定位搜「更多同一风格」的，不要再找跑偏方向。可多轮累积。
2. 打开 Dribbble 搜索（如 `dribbble.com/search/<关键词>`，关键词用 `-` 连接或 URL 编码）。
   - **浏览器工具**：若是操作台触发的 headless 后台 agent，**没有浏览器 MCP**（playwright MCP / claude-in-chrome 都不可用）——别去 ToolSearch 找 MCP，直接用本机已装的 **Python Playwright（chromium headless）** 写脚本抓，或用 `playwright-cli` skill。交互式 CLI 会话里若有 MCP/浏览器可正常用。
3. 对 6-9 个代表性结果：**点进作品详情页，解析出真实大图 URL（详情页主图 `<img>` 的 src，一般是 cdn.dribbble.com 高清图），用 curl/playwright 下载这张高清原图**存进 `artifacts/phase-2/refs/<n>.png`（先 `mkdir -p`）。挑参考优先覆盖不同风格倾向，给对比空间。
   - **不要截图兜底**：某张取不到真实高清图 URL 就跳过它（宁可少几张，不存模糊截图/空白图）；整体访问失败（打不开 Dribbble、一张真图都没拿到）就**不要 done-request**、不登记任何东西，直接结束并明确说「访问失败」——前端会提示用户重试。
4. 逐张登记，每张一句话描述 + 来源用**作品详情页 URL**（用户可点开看原帖）：

```bash
mkdir -p artifacts/phase-2/refs
$PF explore add-ref artifacts/phase-2/refs/1.png --title "<一句话描述这张的风格/亮点>" --source "<dribbble URL>"
# …每张一条…
```

5. 全部登记完，清掉自己这一槽的请求（带 `--kind`，不动 Phase 3 的 `gen-heroes` 槽）：

```bash
$PF explore done-request --kind search-refs    # 网页轮询到该槽清空即知完成，参考自动出现在向导里供用户多选
```

版权红线同 Phase 1：参考只供风格判断、给用户挑感觉用，**不抄袭、不盗图、不进最终产品**。

## 检查点

阶段结束依次执行，顺序不可乱（先读消息再关阶段，避免漏掉用户在网页端的最后意见）：

1. `python3 "$SKILL_DIR/scripts/pf_state.py" inbox` 读网页端消息，逐条 `python3 "$SKILL_DIR/scripts/pf_state.py" reply "<回应>"`；涉及参考增删/重选的，先落实到 `explore`（`add-ref` 或确认 `selectedRefs`）再继续。
2. 确认本阶段产物全部登记：`artifacts/phase-2/refs/*.png` 都已 `explore add-ref`；`explore show` 里 `selectedRefs` 非空（用户已选定）。
3. `python3 "$SKILL_DIR/scripts/pf_state.py" phase 2 --status done`
4. `python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 2 done: references found and selected"`
5. CLI 向用户汇报：找了几张参考、选中哪几张及理由、它们的共同风格倾向；请用户确认后进入 Phase 3 首图设计（见 phase-3-hero.md）。用户已明确"全自动"则不停留。
