# Phase 3 — 首图设计

进入 Phase 3（首图设计）时读本文件：本阶段的目标是**按 Phase 2 选定的参考（`selectedRefs`）生成首图候选——即「选定平台的关键屏纯 UI 设计稿」，让用户定下一张作为整套设计的视觉基调**。

这里定下的首图不只是 hero 区的一张图——它**确立了整套设计的视觉基调（色板 / 字体气质 / 留白 / 质感 / 构图语言），供 Phase 4 页面设计直接复用**。它必须是**选定平台的纯 UI 设计稿本身**（界面铺满画面、正视、无背景/无场景/无设备外框），平台由 `wizard.json` 的 `primary` 决定（缺失则从 `brief.json`/产品定位推断）。Phase 4 不再重新探索风格，而是以本阶段定稿的视觉基调为输入展开。所以首图选得准，下游页面设计才连贯统一。

本阶段只负责"生首图 + 定基调"，不找参考（那是 Phase 2，已完成），不做完整页面设计（那是 Phase 4）。产物全部落在 `artifacts/phase-3/heroes/`。

## 前置条件

- 最佳情况：`explore.json` 的 `selectedRefs` 非空（用户已选定参考），以它们的共同风格为锚点。
- **零输入也要能做**（`selectedRefs` 为空，用户在操作台直接点了「生成首图」）：有 `refs` 就综合所有 refs 的共同风格；refs 也没有就按 `brief.json` 的产品定位/目标用户自定一个贴切风格。**不要因为没选参考就停下不做**——可以在生成后用 `choice ask` 让用户在几版里挑，或提示去 ② 选参考做更贴合的下一轮。
- 本阶段依赖 **openai-image-gen** skill + 图像 API key。**先确认该 skill 在当前可用 skill 列表里**——不在、或没有图像 API key 时，退化为：用 design-taste-frontend 直接出 hero 区 HTML 截图作为视觉基调载体，并 log 一句原因。**不要假设 `~/.claude/skills/openai-image-gen/` 路径一定存在然后硬跑**（不同 agent/插件安装位置不同，照跑会 No such file）。下文 `$GEN` 代表该 skill 的 `gen.py` 实际路径（Claude Code 典型为 `~/.claude/skills/openai-image-gen/scripts/gen.py`，以实际为准）。

## 阶段启动

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 3 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 3 started: generating hero images from selected refs"
```

## Step 1: gen-heroes — 生成首图候选

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 3 gen-heroes --status active
```

读 `explore.json` 的 `selectedRefs` → 找到对应参考图、**总结它们的共同风格**（配色 hex / 字体气质 / 布局 / 质感）→ 用 openai-image-gen 按这个风格 + 产品主题生成 2-4 版首图。**用户在操作台发起 gen-heroes 请求时**走下面「首图生成协作」节；**用户直接在 CLI** 时也按同样动作做，只是不用清前端请求槽。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 3 gen-heroes --status done
```

## Step 2: pick-hero — 定首图 · 视觉基调

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 3 pick-hero --status active
```

让用户从生成的首图候选里**单选一张**。挑选期间多跑 `inbox`。

- 网页向导：用户选定、点「进入项目」后，`explore.json` 的 `selectedHero` 记录其选择，跑 `explore show` 可见。
- CLI / 全自动：用 `explore select-hero <hero id>` 写定稿（**别手改 explore.json**；id 来自 `explore show` 的 `heroes[].id`，落库会自动存成其 file 路径）：
  ```bash
  python3 "$SKILL_DIR/scripts/pf_state.py" explore select-hero hero-1a2b3c
  ```
  CLI：用户报编号 → 换成 id → `select-hero`。全自动：自选与 `selectedRefs` 风格最贴合、最能承载产品调性的一张 → `select-hero` → log 理由。

选定后，**把这张首图的视觉基调显式落成一段文字**——色板（几个 hex）、标题/正文字体气质、留白密度、圆角与阴影、构图语言——写进 `explore` 的 styleSummary（若协作节里已写则确认/补全），并在 log 里点明"此为 Phase 4 页面设计的视觉基调输入"。这一段就是交给 Phase 4 的合同，不要只留"按 hero 2"。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 3 pick-hero --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "Hero picked: hero-2 定稿，视觉基调（冷色玻璃拟态/大留白/粗无衬线）传给 Phase 4 页面设计"
```

## 首图生成协作

用户在操作台走到「首图设计」步时，会在网页上请求 Agent 协作。请求出现在 `inbox`（`type: "explore-request"`），同时 `.productflow/explore.json` 的 `request` 字段按 kind 分槽记录——本阶段对应 `gen-heroes` 槽。**会话里每个检查点都顺手 `$PF inbox`，看到 `gen-heroes` 请求就处理**：

```bash
PF="python3 $SKILL_DIR/scripts/pf_state.py"   # 已 export PF_PROJECT
$PF explore show      # 看 request（含 gen-heroes 槽）、用户选中的参考(selectedRefs)、已登记的 heroes
```

**请求 `gen-heroes`（按选中参考生成首图）**，按序执行：

1. 读 `explore.json` 的 `selectedRefs` → 找到对应参考图文件（`refs` 列表里有 file 路径）。
2. **总结它们的共同风格**（配色 / 字体气质 / 布局 / 质感），写进 explore：

```bash
$PF explore set-summary "极简 + 冷色玻璃拟态 + 大留白 + 无衬线粗标题"
```

3. 用 openai-image-gen 按这个风格 + 产品主题生成 2-4 版首图，存 `artifacts/phase-3/heroes/<n>.png`（先 `mkdir -p`）。

   **首图 = 选定平台的关键屏纯 UI 设计稿**（不是营销长图、不是 lifestyle mockup）。先读 `.productflow/wizard.json` 的 `primary` 确定平台（缺失则从 `brief.json`/产品定位推断），按平台出对应纯 UI：

   | 主平台 | 出什么 | `--size` |
   |--------|--------|----------|
   | **APP** | 手机 App 原生界面，竖屏 ~9:19.5，状态栏/导航/底部 Tab 作为 UI 一部分 | `1080x2340` |
   | **H5**  | 移动 web 界面，竖屏 ~9:19.5，网页式导航/页脚，无浏览器地址栏 | `1080x2340` |
   | **PC**  | 桌面 web 界面（首屏/关键屏），横向，1440 宽基准，无浏览器窗口框 | `1440x1080` |

   ⛔ **纯 UI 硬约束**：界面铺满画面、正视、edge-to-edge；**禁止**背景环境/使用场景/lifestyle 摄影/设备外框（手机在手、笔记本在桌）/浏览器窗口框/营销 case-study 长页场景模板（**不要**用 `ui-mockups/landing-page-case-study.md` 这类场景模板）。

   ⚠️ **必须用 `--prompt` 模式，不要 `--subject ... --category web-design`**——`--subject`+`--category` 会被 `styles.json` 里 web-design 风格自动追加「browser window / desktop frame / background / mockup / isometric」等措辞，正好把背景和设备框塞回来、与纯 UI 矛盾。把产品本质 + 平台界面描述 + 风格 + 上面所有约束揉成**一条完整 prompt** 传给 `--prompt`：

```bash
GEN=<openai-image-gen 的 scripts/gen.py 实际路径>
mkdir -p artifacts/phase-3/heroes
python3 "$GEN" \
  --prompt "<产品一句话> 关键屏纯 UI 设计稿, <平台界面描述>, <上面总结的风格描述>, pure UI design, fills the frame edge-to-edge, flat, no background scene, no device frame, no browser chrome, front view" \
  --size <按平台: APP/H5=1080x2340, PC=1440x1080> \
  --count 4 --model gpt-image-2 --out-dir artifacts/phase-3/heroes
```

4. 逐张登记，每张标注风格：

```bash
$PF explore add-hero artifacts/phase-3/heroes/1.png --style "玻璃拟态 hero"
# …每张一条…
```

5. 全部登记完，清掉自己这一槽的请求（带 `--kind`，不动 Phase 2 的 `search-refs` 槽）：

```bash
$PF explore done-request --kind gen-heroes    # 网页轮询到该槽清空即知完成，首图自动出现在向导里供用户单选
```

版权红线同前阶段：参考只供风格判断，生成的首图文案与素材必须是本产品自己的，不抄竞品文案、不盗图。

## 检查点

阶段结束依次执行，顺序不可乱（先读消息再关阶段，避免漏掉用户在网页端的最后意见）：

1. `python3 "$SKILL_DIR/scripts/pf_state.py" inbox` 读网页端消息，逐条 `python3 "$SKILL_DIR/scripts/pf_state.py" reply "<回应>"`；涉及重新生图/换风格的，先落实到 `explore`（`set-summary` + 重新 `add-hero`）再继续。
2. 确认本阶段产物全部登记：`artifacts/phase-3/heroes/*.png` 都已 `explore add-hero`；`explore show` 里 `selectedHero` 非空（用户已定稿）、`styleSummary` 写明了视觉基调。
3. `python3 "$SKILL_DIR/scripts/pf_state.py" phase 3 --status done`
4. `python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 3 done: hero finalized, visual tone set for Phase 4"`
5. CLI 向用户汇报：生成了几版首图、定稿哪张及理由、由它确立的视觉基调要点（色板 / 字体 / 质感）；强调这套基调将被 Phase 4 页面设计复用。请用户确认后进入 Phase 4 页面设计（见 phase-4-design.md）。用户已明确"全自动"则不停留。
