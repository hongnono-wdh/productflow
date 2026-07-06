# 还原度方案 · 专题 B — 组件库全链路（选型 / 定位 / 锁定 / 使用）

> 把主纲里散在 R-①b/②b/④b/⑥a 的组件库线索，落成**可实施的完整机制**。对齐 8 阶段流水线（⑥=前端实现 `phase-6-frontend.md`）、`choice ask` 机制、`design-spec.componentLib`（专题 A）、`impl-check` 式硬闸。
> 核心思想（用户洞察 + Halodoc 生产验证）：**设计与开发共用同一套现成组件库 + token**，还原度从「事后对比」变成「天生同源」。Halodoc 用「组件目录 + 映射优先级 + pre-flight 门」达 80–90% 保真。

---

## B0. 组件库在方案里「是什么」

不是自造，而是**选用现成成熟库**，在项目里以两样东西存在：

1. **机器可读的「组件目录」**（component catalog，借鉴 Halodoc `DS_AGENTS.md` / v0 registry）——喂给 AI 读，告诉它「本项目选了哪套库、有哪些组件、每个干什么、什么场景用哪个」。**这是核心落地物。**
2. **库本身作为项目依赖**——⑥ 真正 `import` 的代码。

| 平台 | 库 | 形式 |
|---|---|---|
| Web / 桌面 | shadcn/ui + Tailwind | copy-paste 组件进仓库 |
| iOS | SwiftUI 系统组件 + HIG | 系统自带，不引三方 |
| Android | Material 3 Compose | 系统自带 + Theme Builder 生成主题 |

---

## B1. 怎么选择、怎么定位（三输入决策）

选型由三个输入驱动，写进 `design-spec.componentLib`：

- **① 产品类型（profile 信号，来自 ① / `wizard.json`）** → 定「要不要重组件化 + 哪类库」：SaaS/dashboard/工具 → 组件密集库（shadcn/Material）；纯营销/落地 → 轻库或偏定制。
- **② 平台（`wizard.json.platforms`）** → 定「候选池」：Web→shadcn/Radix/MUI/Ant；iOS→SwiftUI+HIG（近唯一）；Android→Material3（近唯一）；桌面→复用 Web。
- **③ 参考风格（②萃取的视觉调性）** → 定「具体哪套 + 什么主题」：从参考图萃取的风格匹配最接近的库/主题预设。

**定位公式**：产品类型定「重组件化程度 + 哪类库」 → 平台定「候选池」 → 参考风格定「具体库 + 主题」。

**各平台默认库表（§6 已定，实施期可调）**：

| 平台 | 默认库 | 主题机制 |
|---|---|---|
| Web / 桌面 | shadcn/ui + Tailwind | Tailwind theme + CSS var（token 注入） |
| iOS | SwiftUI 系统组件 + HIG | token 注入到 `.font`/`Color` |
| Android | Material 3 Compose | Theme Builder 直出 `Color.kt`（与 token 对齐） |

---

## B2. 怎么选中（阶段 + 机制）

两步、跨两阶段：

- **`①b 萌芽`（市场调研）**：按产品类型给**候选库家族**，`spec set-lib --platform X --lib "<候选>"`（候选态）。
- **`②b 锁定`（找参考）**：结合萃取风格，从候选**定稿** + 产出组件目录。

**锁定机制 = `choice ask` 让用户拍板（新增决策点，建议）**，与 ⑤ 选模板 / ⑧ 选部署目标同一套：

```bash
ID=$(python3 pf_state.py choice ask --stage 2 \
      --question "本项目 Web 端建议用 shadcn/ui + Tailwind（理由：SaaS 工具型、参考风格偏简洁），是否采用？" \
      --option "采用 shadcn/ui" --option "改用 Ant Design" --option "改用 MUI")
python3 pf_state.py choice wait "$ID" --timeout 600
# 用户点选后：spec set-lib 定稿 + 生成组件目录
```

**全自动模式**（用户已声明「全自动」）：跳过 choice、按推荐自动 `set-lib` + `log` 说明理由。

---

## B3. 组件目录格式（component catalog）

- **位置**：`artifacts/phase-2/component-catalog.md`（人可读）+ 关键索引进 `design-spec.componentLib[platform].catalog` 指向它。
- **产出**：②b 锁定后由 agent 生成（对选定库，列出会用到的组件）。
- **格式（对齐开源事实标准、不自创）**：机器可读部分对齐 **shadcn `registry.json` / v0 registry spec**（AI 生态已熟悉、v0 等工具原生消费的格式）；另配人读 `component-catalog.md`（借鉴 Halodoc `DS_AGENTS.md`）。每组件一条：

```markdown
## Button
- import: `import { Button } from "@/components/ui/button"`   (Web)
- iOS 等价: SwiftUI `Button { } label: { }`（.buttonStyle(.borderedProminent) = primary）
- Android 等价: Compose `Button(onClick) { Text() }`
- 用途: 主行动号召 / 次级操作
- variants: primary(默认CTA) / secondary / ghost / destructive
- props: size(sm|md|lg), disabled, loading
- token: 背景=color.action.primary, 圆角=radius.md
- 什么场景用: 表单提交、CTA、对话框确认；**不要**用于纯导航（用 Link）

## Card / Input / Dialog / ...（同格式）
```

- **层级标注**（映射优先级用）：每组件标 `level: organism|molecule|atom`。

---

## B4. 怎么使用（⑥ 前端实现，Halodoc 验证路径）

1. **pre-flight 硬门**：⑥ scaffold 前校验组件目录 + `componentLib` 存在——缺则 **block**（新增 `spec check` 已含「缺 lib 报错」，见专题 A5；可加 catalog 文件存在性校验）。**不许 AI 裸写 CSS / 裸用 Apple primitive。**
2. **映射表 + 确认门**：AI 先出「本页每个设计元素 → 组件目录里哪个组件（什么 variant）」映射，写进 `design-spec.pages[].components`（`spec set-page --component slot:lib:variant`）。原理：**改错映射远比改错代码便宜**。全自动模式跳过人工确认、直接写。
3. **映射优先级**：优先高层（organism→molecule→atom）；**匹配不上 → 报缺口、不静默用最近似的**（静默近似=还原度差之源）。缺口进 `log`/`inbox` 提示。
4. **token 注入**：组件的色/间距/圆角走 `spec compile` 出的 token 文件（专题 A4），**不硬编码**。
5. **兜底**：库里真没有的独特件（尤其营销页视觉）→ 定制 / 生图素材（B5）。

**各平台使用差异：**

| 平台 | 怎么用 |
|---|---|
| Web / 桌面 | `import` shadcn 组件 + `tokens.css` 变量 |
| iOS | SwiftUI 系统组件（List/NavigationStack/Button…）按 catalog 对应 + `Tokens.swift` |
| Android | Material3 Compose 组件 + `Tokens.kt`（Theme Builder 对齐） |

---

## B5. 营销页特例（骨架组件化 + 只生图素材，已定决策）

`design-spec.pages[].type == "marketing"` 时：

- **骨架组件化**：排版/CTA/栅格/间距用组件 + token（同产品 UI）。
- **只生图「独特视觉素材」**：hero 大图 / 背景纹理 / 氛围图 → `gpt-image` 生成，记 `pages[].assets[{slot, gen, file}]`，再嵌进组件骨架（如 `<Hero bg={asset}>`）。
- **④ 出图指令收窄**：营销页 gen.py 从「生成整页 UI」退回「生成图片素材」——`--prompt "<素材描述>, 独立视觉素材, 透明/纯色背景, 无 UI 控件"`，不再整页临摹。
- **收益**：改文案不用重生图、可 A/B、token 不漂移、不遗传还原度病。

---

## B6. 降级路径

- **某平台无成熟组件库生态**（冷门场景）：回退到「direction.md 文字 + token」手写，`log` 说明；不 block 整条流水线。
- **组件目录缺失但库已锁**：⑥ 可只靠 `componentLib.lib` + token 生成（弱于有目录，但可跑），`log` 提示补目录。
- 遵循项目「新增依赖要给降级路径，不硬报错」惯例。

---

## B7. 与现有机制的接点

- **choice**：复用 `choice ask/wait`（B2），无需新 API。
- **pre-flight 门**：扩 `spec check`（专题 A5）加 catalog 存在性；被 `phase 6 --status done` 硬闸引用（同 `impl-check` 模式）。
- **映射写入**：复用专题 A 的 `spec set-page --component`。
- **profile 信号**：读 `wizard.json.platforms/primary` + brief 产品类型 → 选型输入（B1），与主线 A 同源。

---

## B8. 落地清单

- [ ] ①b/②b 手册：候选库萌芽 + `choice ask` 锁库 + 生成组件目录（改 `phase-1`/`phase-2`，见专题 E）
- [ ] `spec check` 加 catalog 存在性校验 + 缺 lib block（专题 A5 已含缺 lib，补 catalog）
- [ ] ④ 手册：映射表产出 `spec set-page --component`；营销页素材 `--asset`（专题 E）
- [ ] ⑥ 手册（`phase-6-frontend.md`）：pre-flight → 映射优先级 → token 注入 → 兜底（专题 E）
- [ ] gen.py 营销页素材指令模板（B5）
- [ ] 组件目录模板文件（B3 格式）随 skill 分发，供 agent 参照
- [ ] 测试：choice 锁库往返、`spec check` 缺 catalog 负例
