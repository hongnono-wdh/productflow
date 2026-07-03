# 还原度方案 · 专题 D — 状态矩阵（9 态交互 + ⑤ 数据态）

> 细化主纲 `R-④d`（交互态）+ `R-⑤a`（数据态）。落进 `design-spec.pages[].states`（专题 A schema）。
> 核心（调研 1/3）：**漏状态是还原度最大杀手**——设计稿只画 default 态，⑥ 实现时其余态全靠猜。而 **AI 被强制生成全状态，反而比疲劳的人更不会漏**——把人类弱项变成 AI 的机械强项。

---

## D0. 为什么

- 设计师/AI 画的是 happy path（理想数据、default 态）；开发要处理所有路径（空/载/错/多）。这条鸿沟是「功能对、体验错」的根源，也是还原度差最常被跳过的一步。
- 对策：把状态**显式列进 spec、做成强制 gate**，让 ⑥ 逐态实现、逐态验收。

---

## D1. 两类状态、两个阶段

| 类 | 阶段 | 内容 | 写入 |
|---|---|---|---|
| **交互态** | ④ 页面设计（组件层） | default / hover / focus / active / disabled / loading / error / empty / skeleton | `spec set-page --state <comp:s1,s2>` |
| **数据态** | ⑤ 功能数据（数据层） | 空数据 / 单条 / 多条(溢出) / 长文本截断 / 分页边界 | `spec set-page --state <comp:...>` 追加 |

两者都进 `design-spec.pages[].states`（专题 A schema 的 `states` 字段）。

---

## D2. 组件类型 → 必需状态（分级，避免 9 态全强制过重）

不是所有组件都要全 9 态。按类型定必需集：

| 组件类型 | 必需状态 |
|---|---|
| **交互控件**（Button/Input/Select/Toggle） | default / hover / focus / disabled（+ Button：loading；+ Input：error） |
| **数据容器**（List/Table/Card grid/Feed） | default / **empty** / **loading**(skeleton) / 多条溢出 / 长文本截断 |
| **表单**（Form） | default / submitting / error / success + 逐字段校验错 |
| **导航**（Nav/Tab/Menu） | default / active(当前项) / hover |
| **静态展示**（Hero 文案/Footer/静态区块） | default（够了） |

`spec check` 可加：数据容器类组件**缺 empty/loading → 警告**（缺态 gate，D4）。

---

## D3. 各平台落法

| 状态 | Web | iOS(SwiftUI) | Android(Compose) |
|---|---|---|---|
| hover | `:hover` | （移动端无，跳过） | （无） |
| focus | `:focus-visible` + `aria` | `@FocusState` | `Modifier.focusable` |
| disabled | `[disabled]` + `aria-disabled` | `.disabled(true)` | `enabled=false` |
| loading | skeleton / spinner | `ProgressView` / redacted | `CircularProgressIndicator` / placeholder |
| empty | 空态插画+引导 | 空态 View | 空态 Composable |
| error | 错误提示（`aria-live`） | alert / inline | Snackbar / inline |

**平台差异纪律**：hover/focus 是 Web 概念，移动端用 pressed/focus 替代——`states` 在 ④ 按平台裁剪（同一页 PC 版要 hover、APP 版不要）。

---

## D4. 强制 gate（缺态阻断）

- **④ 出 spec 时**：`spec check` 校验「数据容器类组件是否有 empty+loading」——缺则警告（`--strict` 升为 error，挡住进 ⑤）。
- **⑥ 验收时**（接专题 C）：
  - 第 1 层 LLM 裁判 checklist 第 7 轴「组件状态」——判实现是否只做了 default、漏了 spec 里声明的态。
  - 第 3 层 DOM 断言——对「关键态可枚举」的做断言（如空态提示文案存在、error 态 `aria-live` 存在、disabled 属性正确）。
- **截图策略**：状态多、逐态截图会爆炸——**只对关键态截图**（default + empty + error 各一张，进 P6-5 对比），其余态靠 DOM 断言覆盖（专题 C4）。

---

## D5. ⑤ 数据态 → UI 边界（R-⑤b）

⑤ 定数据模型时顺带定「UI 数据边界」，避免 ⑥ 用假数据撑出跑版布局：

- 列表**典型/最大条数**（决定要不要虚拟滚动、分页）
- 字段**最大长度 / 截断规则**（长标题省略号 vs 换行）
- **可空字段**的空态呈现
- 写进 `states` 或页 note，⑥ 用真实边界数据渲染 + 截图。

---

## D6. 与其它专题接点

- **A**：状态存 `pages[].states`；`spec check` 加缺态校验（D4）。
- **C**：状态进第 1 层裁判 checklist（轴 7）+ 第 3 层断言；关键态截图进对比。
- **④/⑤ 手册**（专题 E）：④ 出交互态、⑤ 补数据态。

---

## D7. 落地清单

- [ ] ④ 手册（`phase-4-pages.md`）：出每页组件的交互态 → `spec set-page --state`（专题 E）
- [ ] ⑤ 手册（`phase-5-spec.md`）：补数据态 + UI 数据边界（专题 E）
- [ ] `spec check`：数据容器缺 empty/loading 校验（D4）
- [ ] 组件类型→必需状态映射表（D2）随 skill 分发供 agent 参照
- [ ] ⑥ 验收：状态进裁判 checklist + DOM 断言（并入专题 C）
- [ ] 测试：`spec set-page --state` 往返、缺态校验负例
