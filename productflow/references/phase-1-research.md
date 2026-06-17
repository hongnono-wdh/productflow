# Phase 1 — 市场调研与截图复刻

> 何时读本文件：用户提出新产品需求、流水线即将进入或正处于 Phase 1（市场调研）时，先通读本文再动手。

本阶段目标：搞清楚"做什么产品、给谁看、像谁但不抄谁"，产出竞品矩阵与复刻要点，作为 Phase 2 设计的唯一输入。没有这一步，Phase 2 只能凭空设计，产出大概率是模板味的 AI slop。

> 产出范围：ProductFlow 做的是**完整互联网产品**——从落地页、官网，到带数据库与后端的功能性 Web 应用（落地页只是最简单的一种，对应后面模板里的 T1）。本手册下文为表述简洁常以"落地页/页面"举例，但同一套调研方法适用于多页站点与带后端的应用；功能、数据、后端在 Phase 5/6 展开，部署在 Phase 7。

## 阶段启动

若这是流水线第一阶段且 `.productflow/` 尚不存在，先初始化：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" init --product "产品名"
```

然后标记阶段开始：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" phase 1 --status active
python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 1 市场调研启动"
```

本阶段产物目录约定（路径均相对 `.productflow/`）：

```
artifacts/phase-1/
├── positioning.md          # 产品定位对齐结果
├── screenshots/<域名>.png  # 竞品整页截图
├── analysis/<域名>.md      # 单竞品分析卡片
├── core-analysis.mm.md     # 核心矛盾分析导图（markmap 源，面板可交互渲染）
├── competitors.md          # 竞品矩阵（阶段汇总产物之一）
└── replicate-notes.md      # 复刻要点（阶段汇总产物之二，Phase 2 直接消费）
```

---

## Step 1: define-product — 与用户对齐产品定位

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 define-product --status active
```

先确认三件事，缺一不可——它们直接决定竞品筛选标准和后续设计方向：

1. **一句话定位**：这是什么产品，解决什么问题（例："给独立开发者的 API 监控工具"）。
2. **目标用户**：谁会打开这个落地页（决定文案语气与视觉风格的雅俗取向）。
3. **转化目标**：落地页希望用户做什么（注册 / 预约 demo / 加 waitlist / 直接付费——决定 CTA 设计与区块顺序）。

任何一项缺失：**先问用户，不要默默猜**。用一条消息把缺的项一次问完，避免来回打断。

**全自动模式例外**：用户明确说过"全自动 / 不要停"时，不提问，基于已有上下文给出最合理假设，并把假设**显式写进** `artifacts/phase-1/positioning.md`（标注"假设，未经用户确认"）。这样用户事后在操作台能看到假设依据，发现偏差可及时纠正。

完成后落产物并收尾：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 1 artifacts/phase-1/positioning.md --title "产品定位"
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 define-product --status done
```

### 操作台「产品需求」向导协作（用户在网页发起时处理）

用户在操作台新建项目走到「产品需求」步时，会填一段产品描述、点「✦ 生成摘要」，请你（CLI 侧的 Agent）把这段描述提炼成一份四字段理解摘要回填到网页。请求出现在 `inbox`（`type: "brief-request"`），同时 `.productflow/brief.json` 的 `request` 字段记录当前请求与用户原始描述。**会话里每个检查点都顺手 `$PF inbox`，看到 brief-request 就处理**：

```bash
PF="python3 $SKILL_DIR/scripts/pf_state.py"   # 已 export PF_PROJECT
$PF brief show     # 看 description（用户原始描述）和当前 request
```

读 `description`，按产品思维把它提炼成四个字段——**不是复述原文，是提炼判断**：

- **goal（产品目标）**：这个产品到底帮用户达成什么（一句话，动词开头）。
- **users（目标用户）**：谁会用、什么场景下用。
- **need（核心需求）**：用户最痛的那一两个真实需求（呼应 core-analysis 的"真问题"思路）。
- **scope（输出范围）**：这次要产出的落地页/页面范围（可结合用户选的平台 PC/H5/APP）。

描述太空泛、判断不了核心需求时，宁可在某字段写「需向用户确认 X」也不要硬编。写回后清请求，网页轮询到 `ready=true` 即把四行摘要回填到向导供用户确认：

```bash
$PF brief set-summary \
  --goal "帮自由职业者轻松开票收款" \
  --users "自由职业者 / 独立顾问，按项目结算" \
  --need "快速生成规范发票、跟踪付款状态" \
  --scope "PC 落地页 + H5"
# set-summary 自动把 ready 置 true、清空 request；网页无需刷新即显示
```

这份摘要等价于 define-product 的产出——用户在向导里确认后，直接作为本阶段 positioning.md 的草稿基础，不必再重复问一遍定位三件事。没有走向导（用户直接在 CLI）时，本节跳过，照上面的 define-product 正常对齐。

## Step 2: search-competitors — 竞品发现

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 search-competitors --status active
```

用 WebSearch 找同品类产品，两条线并行：

- **直接搜品类**：`"<品类> tool"`、`"<品类> alternatives"`、`"best <品类> 2026"` 等。
- **AI / 产品目录站**：Product Hunt、There's An AI For That、futurepedia 等目录页，按品类翻代表性产品。

筛选 **3-6 个**代表性竞品的**落地页 URL**（不是 dashboard、不是 docs 页）。筛选标准：

- 与本产品定位/用户群重叠度高，至少 1 个是品类头部（学最佳实践），至少 1 个是新锐（学当下流行风格）；
- 落地页本身设计质量过关——分析烂页面学不到东西；
- 风格之间有差异，避免选出 5 个长得一样的，后面给不出风格候选。

把候选 URL 列表 + 一句话入选理由记下来（可直接写入后面的 competitors.md 草稿），然后：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 search-competitors --status done
```

## Step 3: capture-screenshots — 截图采集

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 capture-screenshots --status active
```

用 **webapp-testing** 或 **playwright-cli** skill（headless）逐个打开竞品 URL，做**整页截图**（full-page，不是首屏），保存为：

```
artifacts/phase-1/screenshots/<域名>.png    # 如 screenshots/linear-app.png，域名中的点换成连字符
```

采集要点：

- 桌面视口（1440 宽左右）截整页；整页截图是后续分析版式结构的依据，首屏截图看不到区块顺序。
- 等待页面完全加载（懒加载图片、动画入场）再截，否则截到一半空白。
- 某个 URL 打不开或反爬：换下一个候选竞品补位，不要在单个站上耗超过 2 次重试。

**每张截图逐个登记**——操作台靠 artifact 索引展示图片，漏登记用户就看不到：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 1 artifacts/phase-1/screenshots/<域名>.png --title "竞品截图 - <产品名>"
```

全部截完：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 capture-screenshots --status done
python3 "$SKILL_DIR/scripts/pf_state.py" log "已采集 N 个竞品整页截图"
```

### APP 类项目：补抓 App Store / Google Play 官方特色截图

**仅当主平台是 APP**（读 `wizard.json` 的 `primary`，或 `platforms` 以 APP 为主；CLI 项目从产品定位判断）才做这一步——APP 竞品的"落地页"其实是商店上架页，开发者上传的截图就是这个 App 最核心的几屏真实界面，比竞品官网直观得多。用本 skill 自带脚本抓官方截图（免鉴权：iOS 走 iTunes API、Android 抓 Play 上架页）：

```bash
python3 "$SKILL_DIR/scripts/appstore_shots.py" --platform both \
  --term "<产品品类英文词，如 habit tracker / budgeting app>" \
  --out artifacts/phase-1/appstore --limit 3 --max-shots 6
# 已知某竞品 App 时更准：iOS 用数字 trackId、Android 用包名
#   --platform ios --id 1234567890     /   --platform android --id com.foo.bar
```

脚本把每个 App 的截图存进 `artifacts/phase-1/appstore/<ios|android>-<app>/`，并写 `manifest.json`。逐个登记成产物（这样操作台画廊能看、且会作为 ② 找参考的**真实 App 界面参考**来源）：

```bash
# 按 manifest.json 列出的文件逐张登记
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 1 artifacts/phase-1/appstore/<子目录>/<n>.png --title "<App名> 商店截图 N"
```

注意：iOS（iTunes API）稳定可靠；Android（抓 Play 页 HTML）best-effort，可能因地区/反爬少抓或抓空——抓不到就跳过、别卡住，桌面/官网竞品分析照常进行。截图仅供学习界面结构与卖点呈现，**不抄袭、不进最终产品**。

## Step 4: analyze-style — 多竞品分析

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 analyze-style --status active
```

每个竞品都按下面的四维度独立分析（各读各的截图）。**默认串行逐个做即可**——竞品分析互相独立，串行结果和并行一样，只是慢些。

**可选加速**：若你的 agent 支持并行子代理（如 Claude Code 的 Agent Teams `TeamCreate`），且竞品 ≥ 3 个，可每个子代理分 1-2 个竞品并行分析，完后清理（`TeamDelete`）。spawn 子代理时给足上下文：产品定位（positioning.md 内容）、分到的截图绝对路径、输出文件路径、四维度模板——子代理不继承对话历史，少给一项就只能瞎编。**没有并行能力就串行，不要去调用不存在的工具**。

每个竞品输出一张分析卡片 `artifacts/phase-1/analysis/<域名>.md`，固定四个维度：

1. **版式结构**：从上到下的区块顺序（hero → social proof → features → pricing → FAQ → footer 之类），各区块的布局型式（左右分栏 / 居中 / bento grid…）。
2. **风格要素**：配色体系、字体气质（衬线/无衬线、字重对比）、留白密度、圆角/阴影/插画风格、动效线索。
3. **卖点文案骨架**：标题在回答什么问题、副标题承接什么、卖点的组织逻辑（痛点式 / 功能式 / 对比式）。**只提炼骨架结构，逐字文案不抄录**。
4. **转化设计**：CTA 的位置/数量/措辞类型、表单门槛、信任要素（logo 墙、testimonial、数据）摆放策略。

每张卡片登记：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 1 artifacts/phase-1/analysis/<域名>.md --title "竞品分析 - <产品名>"
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 analyze-style --status done
```

## Step 5: core-analysis — 核心矛盾分析

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 core-analysis --status active
```

这是调研阶段的灵魂步骤：**从用户动作出发，不从功能出发**。竞品分析回答"别人长什么样"，本步骤回答"用户到底卡在哪、为什么该用我们"。方法论四问，写成一张 markmap 思维导图 `artifacts/phase-1/core-analysis.mm.md`（`.mm.md` 后缀会被识别为 mindmap 类型，面板内可交互渲染）：

1. **用户在原场域做什么**：把目标用户解决该问题的现有动作拆成树（大类 → 子场景 → 具体动作），每个叶子用圆点标频率×痛感：`●●●●○`（4/5 分）。打点逼你排优先级，没有打点的动作树只是流水账。
2. **核心矛盾（真问题）**：表面诉求之下，用户**愿意付钱或付时间**解决的那个矛盾是什么。一句话写死，不许列三条。
3. **原流程 vs 我们**：现在用户怎么凑合解决（缺陷打点标出最痛的环节）；我们的解法砍掉了哪几步、把什么变成了自动。
4. **傻瓜式使用**：把我们的解法压缩到用户视角的 1-3 步最短路径。写不进 3 步说明产品还没想清楚，回到第 2 问重想。

导图骨架（直接套用，`#`/`##` 作主干、`-` 作枝叶）：

```markdown
# <产品名> 核心矛盾分析
## 用户在原场域做什么
- <动作大类>
  - <子场景/动作> ●●●●○
## 核心矛盾（真问题）
- 表面诉求：…
- **真问题：<一句话>**
## 原流程 vs 我们
- 原流程：<步骤链，最痛环节标 ●●●●●>
- 我们：<砍掉什么、自动化什么>
## 傻瓜式使用
- 1 <用户做的第一步>
- 2 …（最多 3 步）
```

信息来源：positioning.md 的定位 + 竞品分析卡片暴露的共性盲区 + 必要时 WebSearch 用户讨论（Reddit/即刻/V2EX 抱怨帖是真痛点的金矿）。与用户在场时，第 2 问的结论**先说给用户听再写**——核心矛盾认错了，后面四个阶段全白做。

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 1 artifacts/phase-1/core-analysis.mm.md --title "核心矛盾分析"
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 core-analysis --status done
```

## Step 6: replicate-report — 汇总产物

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 replicate-report --status active
```

汇总两份文件，这是本阶段对外交付的核心：

**`artifacts/phase-1/competitors.md` — 竞品矩阵**：一张表，行 = 竞品，列 = URL / 定位一句话 / 区块顺序摘要 / 风格关键词 / 转化策略 / 值得借鉴的一点。让用户 30 秒看完全局。

**`artifacts/phase-1/replicate-notes.md` — 复刻要点**（设计阶段的直接输入，见 phase-2-refs.md 起）：

- **推荐信息架构**：结合产品定位与竞品共性，给出本产品落地页应有的区块清单与顺序，每个区块一句话说明放什么、为什么。hero 区块必须直接回应 core-analysis.mm.md 里的"真问题"，傻瓜式 1-3 步就是 how-it-works 区块的骨架。
- **风格方向候选 2-3 个**：每个候选给名字 + 风格描述 + 引用哪些竞品截图作参照 + 适配理由。给 2-3 个而不是 1 个，是为了让用户在 Phase 2 有真实选择权而非被动接受。
- **转化设计建议**：CTA 策略、信任要素清单。

两份都登记：

```bash
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 1 artifacts/phase-1/competitors.md --title "竞品矩阵"
python3 "$SKILL_DIR/scripts/pf_state.py" artifact 1 artifacts/phase-1/replicate-notes.md --title "复刻要点"
python3 "$SKILL_DIR/scripts/pf_state.py" step 1 replicate-report --status done
```

## 版权红线

复刻竞品只学**布局结构、信息架构、风格思路**。不抄文案（连改写一两词也不行）、不下载/盗用竞品图片素材、不复制 logo 或品牌元素。截图仅作内部分析参照，不进入最终产品。分析卡片里描述文案"骨架"（结构与逻辑），不摘录原句。

## 检查点

阶段收尾按固定顺序执行，不要跳步：

1. **读网页端消息并逐条回应**：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" inbox
   python3 "$SKILL_DIR/scripts/pf_state.py" reply "<对该条留言的回应>"   # 每条留言各回一次
   ```

   有新消息先处理（可能用户在操作台补充了定位信息或否决了某竞品），再继续收尾。

2. **确认汇总产物已登记**：competitors.md 与 replicate-notes.md 都已 artifact 登记（上一节命令）。

3. **标记阶段完成**：

   ```bash
   python3 "$SKILL_DIR/scripts/pf_state.py" phase 1 --status done
   python3 "$SKILL_DIR/scripts/pf_state.py" log "Phase 1 完成：N 个竞品分析，产出竞品矩阵与复刻要点"
   ```

4. **CLI 汇报并等待确认**：向用户汇报本阶段结论（竞品几个、推荐信息架构一句话、风格候选名字），请用户在网页或 CLI 确认后进入 Phase 2 找参考（见 phase-2-refs.md）。用户明确说过"全自动"则不停留，直接进入下一阶段。
