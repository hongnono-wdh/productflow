# 还原度方案 · 专题 C — ⑥ 前端实现的还原度验收

> 把主纲 `R-⑥d/e` 细化到可实施。落在 **⑥ 前端实现**（`phase-6-frontend.md`）。技术最复杂的一份。
> 核心（调研 4 结论）：**不做「设计稿-实现像素相似度% 硬闸门」**（设计稿非金标准 + 2–3% 渲染噪声 + 异源不可对齐 = 拿噪声比噪声）。改用**三层闸门 + 环境确定性 + 3 轮带护栏自纠**（已定：最深档）。

---

## C0. 总架构

```
环境确定性(前置)  →  分治逐组件/区块生成  →  三层闸门  →  ≤3轮自纠  →  人工圈选兜底
                                              ├ 第1层 LLM视觉裁判 (硬gate: 分档pass/fail + 差异清单)
                                              ├ 第2层 uiMatch对齐+diff+DFS (复用开源; 软证据不gate; 喂裁判+给人看)
                                              └ 第3层 DOM/文本断言 (正交硬gate: 可枚举项)
```

判定「能不能标 done」的是**第 1 层（分档）+ 第 3 层（断言）**；第 2 层只给证据。

---

## C1. 环境确定性（最高杠杆，先做）

调研 4：「环境确定性 > 算法选择」。截图前统一渲染环境，否则字体/抗锯齿噪声淹没真实差异。

| 平台 | 固定项 |
|---|---|
| Web/桌面 | 钉死 headless chromium 版本；视口 PC 1440 / H5 390；截图前 `page.evaluate(() => document.fonts.ready)`；禁动画（`animations:'disabled'` + 注入 `*{animation-duration:0s!important;transition-duration:0s!important}`）；mask 动态内容（时间戳/随机头像用固定 seed） |
| iOS | 固定机型（如 iPhone 15）、固定 OS 版本；`xcrun simctl io booted screenshot` |
| Android | 固定 AVD + DPI；`adb exec-out screencap -p` |

设计稿侧（④ 渲染的 PNG 或组件渲染稿）与实现截图**同视口/同尺寸**，为第 2 层对齐做准备。

---

## C2. 第 1 层：LLM 视觉裁判（硬 gate）

**输入**：① ④ 设计稿截图 ② ⑥ 实现截图 ③ `design-spec.pages[].components`（该页应有组件/token）④ checklist。
**输出**：分档 + 结构化差异清单（**不出百分比**，LLM 绝对打分不可靠）。

**checklist 轴（逐轴判，缓解 LLM 拍脑袋总分）**：
1. 布局结构（区块顺序/层级）
2. 主色与配色（对照 spec token）
3. 字体层级（标题/正文字号字重）
4. 关键组件存在性（spec.components 里的是否都在）
5. 间距节奏（留白是否一致）
6. 文案一致（是否错字/占位）
7. 组件状态（是否只做了 default，漏了 empty/error——接专题 D）

**产物**：`artifacts/phase-6/fidelity-<page>.json`（像 test-report 一样可审计）：
```jsonc
{ "page": "pg-1a2b3c", "platform": "PC", "verdict": "pass | needfix | block",
  "diffs": [ { "axis": "spacing", "severity": "minor|major|blocker",
               "desc": "hero 与 features 间距明显大于设计稿", "region": "上部" } ],
  "round": 1, "ts": "..." }
```
`verdict`：`pass`=达标；`needfix`=有 major、进自纠；`block`=有 blocker（缺关键组件/整体错位）。

**谁来判（推荐对抗式）**：新增 server 端专职后台 agent **`_auto_fidelity`**（仿现有 `_auto_arch`/`_auto_action`），spawn 一个**独立** `claude -p` 只做「对比打分、尽量挑毛病」——避免 ⑥ agent 自己判自己偏松。备选（headless 不便 spawn 时）：⑥ agent 流程内自评，但 prompt 强制「以最挑剔的设计师视角逐轴找差异」。

**裁判 prompt 骨架**：
```
你是最挑剔的设计走查（design QA）。用 Read 打开【设计稿】<path> 和【实现截图】<path>，
并读【本页规格】design-spec.pages[pg-x]（应有组件/token）。逐条按 checklist 7 轴对比，
只报真实差异（给 axis/severity/desc/region），最后给 verdict(pass/needfix/block)。
severity=blocker 仅用于：缺关键组件、整体布局错乱、主色完全不符。不要给百分比分数。
输出严格 JSON（schema 见上）。
```

---

## C3. 第 2 层：复用开源 uiMatch 做对齐+diff+评分（软证据，不 gate）

> **分工（已拍板）**：这一层**整体复用开源 uiMatch**（对齐 + pixelmatch + ΔE2000 + DFS 评分 + text-diff），不从零搭；**LLM 视觉裁判（第 1 层）是我们额外加的**——uiMatch 没有语义判定，正好互补（uiMatch 抓像素/位移，LLM 抓语义/布局意图）。

**目的**：兜住 LLM 的结构盲区（调研 4：LLM 会漏「缺失/位移」这类不可命名差异），并给人和裁判可视化证据。**绝不作为 pass/fail 判据。**

**实现 `productflow/scripts/fidelity_diff.py` —— 用成熟开源、不自研 diff 算法**（Pillow 做图像 IO，与现有 redraw 一致；无依赖则整层跳过、降级）：
1. **归一化对齐**：设计稿与实现截图缩放/pad 到同宽——**直接复用开源 [uiMatch](https://dev.to/kosaki08/uimatch-figma-to-implementation-visual-diff-with-playwright-and-ci-1819)**（开源 design-vs-implementation 工具，含 strict/pad/crop/scale 对齐 + pixelmatch + ΔE2000 + DFS 评分 + text-diff，几乎就是本层想做的事）的对齐/评分逻辑。
2. **YIQ 像素差 + 抗锯齿忽略 + 感知色差**：**用现成库、不自研**——`pixelmatch` 的纯 Python 移植（PyPI `pixelmatch`）做像素/抗锯齿，`colour-science` 或 `scikit-image` 做 ΔE2000/SSIM 感知色差。
3. **输出**：`artifacts/phase-6/fidelity-<page>-diff.png`（差异热力图）+ 一个**参考**差异比例数字（仅记录、"疑似大偏差>X% 告警"，不 gate）。
4. 差异图路径写进 `fidelity-<page>.json`，作为裁判输入 + 操作台展示（可接现有 P6-5 对比视图旁边）。

**平台适配**：uiMatch 基于 Playwright 截 Web——**Web/桌面直接用**（这些项目本就有 Node）；**iOS/Android** 用原生截图（`simctl`/`adb`）+ 复用 uiMatch 的对齐/pixelmatch/ΔE2000 算法，或用 `pixelmatch` Python 移植等价实现。`fidelity_diff.py` 只做薄封装（IO + 平台分派 + 无依赖时降级），**不自研 diff 算法**。

---

## C4. 第 3 层：DOM/文本断言（正交硬 gate）

**目的**：像素/LLM 都抓不到的**可枚举确定性项**，用代码断言。

| 检查项 | Web | iOS | Android |
|---|---|---|---|
| 关键文案存在 | `expect(page.getByText(...))` | XCUITest `staticTexts` | Compose `onNodeWithText` |
| spec.components 组件已渲染 | 断言选择器/`data-comp` | `accessibilityIdentifier` | `Modifier.testTag` |
| 必需区块存在 | DOM 断言 | 同上 | 同上 |
| ER 字段落到 UI | 表单字段断言 | 同上 | 同上 |

落成**可复跑测试文件**（不是临时脚本），并入 ⑥ 现有 E2E 套件（`tests/e2e/*`）。与专题 D 的状态覆盖断言共用。

---

## C5. 3 轮自纠闭环（护栏，已定最深档）

```
for round in 1..3:
   截图(环境确定 C1) → 三层闸门(C2/3/4)
   if verdict==pass and 断言全绿:  break ✅
   if 渲染跑不起来:                verdict=block, 本轮0分, 不进对比   # 护栏a
   按 diffs 清单针对性改(只改差异点, 不重做整页)
   if 新一轮 diffs 未比上轮减少/降级:  回退上一版, break             # 护栏b: 只接受确有改进
# 护栏c: 3 轮硬上限
```

- **护栏**（调研 5，防退化/reward hacking）：(a) 渲染失败=硬失败不进对比；(b) 只接受「确有改进」的修订（差异清单条数/严重度下降），否则回退；(c) 3 轮硬上限；(d) 对比用量化信号（差异比例 + 裁判分档），不靠肉眼「差不多」。
- **3 轮后仍 `block/needfix`**：进 `inbox` + 操作台标记，转**人工圈选兜底**（R-⑥f，P6-5 已发版）。
- **驱动方式**：写进 `phase-6-frontend.md` 的 frontend step 收尾流程；`_auto_stage` ⑥ prompt 追加自纠循环指令。

---

## C6. 与硬闸集成

`phase 6 --status done` 前（现有 `impl-check` 硬闸旁）加校验：**每个 `product` 页的 `fidelity-<page>.json` 必须 `verdict==pass`**，否则拒绝标 done（缺陷页需自纠通过或经用户豁免——复用专题 D/现有 `--impl-skip` 的用户批准机制）。营销页视觉素材页放宽（只查骨架组件 + 文案断言，视觉素材不卡像素）。

---

## C7. 各平台差异

| | 截图 | 第1层裁判 | 第3层断言 |
|---|---|---|---|
| Web/桌面 | playwright chromium | 同 | playwright DOM |
| iOS | `simctl io screenshot` | 同（Read 两图） | XCUITest |
| Android | `adb screencap` | 同 | Compose UI Test |

第 1 层裁判跨平台一致（都是「Read 两图 + spec 按 checklist 判」）；差异只在截图和断言工具。

---

## C8. 降级

- **无 Pillow**：跳过第 2 层（软证据），保留第 1（裁判）+ 第 3（断言）。
- **无视觉能力的 agent**：跳过第 1 层，退到第 3 层 DOM 断言 + 人工圈选兜底。
- 均不 block 整条流水线（`log` 说明降级）。

---

## C9. 落地清单

- [ ] fidelity 对比：**复用开源 uiMatch**（对齐+diff+DFS，Web/桌面）+ `pixelmatch` Python 移植（原生端等价）；薄封装 `fidelity_diff.py` 只做 IO/平台分派/降级，**不自研算法**（C3）
- [ ] `_auto_fidelity` 后台裁判 agent（server.py，仿 `_auto_arch`，C2）或 ⑥ 流程内自评
- [ ] `fidelity-<page>.json` 产物结构 + 汇总
- [ ] 第 3 层断言并入 ⑥ E2E 套件（C4）
- [ ] 自纠闭环写进 `phase-6-frontend.md` + `_auto_stage` prompt（C5）
- [ ] `phase 6 --status done` 硬闸加 fidelity 校验（C6）
- [ ] 操作台展示 fidelity 差异图（接 P6-5 对比视图旁）
- [ ] 环境确定性截图脚本（C1）
- [ ] 测试：裁判 JSON schema 往返、diff 归一化、断言负例、自纠护栏（改进才接受）单元测

---

## C10. 诚实边界

- 第 1 层裁判是 LLM，**做分档/找差异靠谱，绝对打分不靠谱**——所以只用分档 + 清单，不用百分比。
- 自纠 3–4 轮后收益衰减（调研 5），故设 3 轮上限 + 人工兜底，不追求「全自动 100%」。
- 保证的是「每页要么裁判判达标、要么你圈选兜底」，**不是「像素级完美」**。
