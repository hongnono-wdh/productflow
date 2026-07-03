# 还原度方案 · 专题 E — 落地清单（手册改动 / 代码改动 / 分期 / 测试）

> 把专题 A–D 汇总成**可执行的实施路线**。对齐 8 阶段（⑥=前端实现）、真实 step-id、代码文件、`tests/` 沙箱、版本号约定。

---

## E1. 六个阶段手册逐个改动点

> 手册双轨：`SKILL.md`/`references/*.md`（Claude Code）与 `AGENTS.md`（Codex）正文一致，改动两边同步（项目惯例）。

### ① `phase-1-research.md`（steps: define-product / search-competitors / analyze-style / core-analysis / replicate-report）
- `analyze-style`：截存竞品关键页真图 → `artifacts/phase-1/refs/`（R-①a，原始像素锚点）。
- `replicate-report` 后：按产品类型**萌芽候选组件库家族** + 起 `design-spec` 骨架 → `spec set-lib --platform X --lib "<候选>"`（R-①b/c）。

### ② `phase-2-refs.md`（steps: style-direction / search-refs / select-refs）
- `select-refs` 后**新增两动作**：
  - **萃取 token**：Read 选中参考图，萃取色板/字体/间距/圆角 → `spec set-tokens --file <草案>`（R-②a）。
  - **锁库 + 组件目录**：`choice ask --stage 2` 让用户拍板选库（全自动则自动）→ `spec set-lib` 定稿 → 生成 `artifacts/phase-2/component-catalog.md`（R-②b，专题 B）。
- 可选：把这两动作显式化为新 step `extract-tokens` / `lock-lib`（`step-add` 幂等注册）。

### ③ `phase-3-hero.md`（steps: gen-heroes / pick-hero）
- `pick-hero` 后：`styleSummary` 结构化 + **首图反萃取精确 token** → `spec set-token color.* --value <真实hex>`（R-③a/b）。

### ④ `phase-4-pages.md`（steps: page-map / design-pages / platform-versions / finalize-direction）
- `design-pages`/`platform-versions`：产品 UI 出**组件映射** → `spec set-page <pg> --type product --component slot:lib:variant`（R-④b）；营销页 → `--type marketing --asset slot:gen:file`，gen.py 只生素材（R-④c，专题 B5）；出**交互态** → `--state comp:s1,s2`（R-④d，专题 D）。
- `finalize-direction`：token **定稿**（`spec set-token`）；`direction.md` 仍写（人读）但机器依据转 `design-spec`（R-④a）。PNG 仍出作预览 + `pages[]` sidecar（渐进决策）。

### ⑤ `phase-5-spec.md`（steps: module-list / er-diagram / schema-ddl / api-contract / pick-template）
- 补**数据态 + UI 数据边界** → `spec set-page --state`（列表条数/长文本截断/空态）（R-⑤a/b，专题 D5）。

### ⑥ `phase-6-frontend.md`（steps: scaffold / frontend）
- `scaffold` 后 **pre-flight**：`spec check`（缺 lib/catalog 报错 block）→ `spec compile --platform all --out artifacts/phase-6/tokens/`（专题 A7/B4）。
- `frontend`：import token 文件 + 按 `pages[].components` 映射拼、**分治逐组件/区块**（R-⑥a/b）；不硬编码色值。
- `frontend` 收尾：**环境确定性截图 → 三层闸门 → ≤3 轮自纠 → 人工圈选兜底**（专题 C 全部）。

---

## E2. 代码改动清单

| 文件 | 改动 | 专题 |
|---|---|---|
| `productflow/scripts/pf_state.py` | `_load_spec` + `cmd_spec` + argparse `spec` 子命令；`spec check`；`phase 6 --status done` 硬闸加 fidelity 校验 | A / C6 |
| `productflow/scripts/token_compile.py`（新） | 一份 token → CSS/Swift/Compose 编译器（纯 stdlib） | A4 |
| fidelity 对比 | **复用开源 uiMatch**（对齐+diff+DFS）+ `pixelmatch` Python 移植（原生端）；`fidelity_diff.py` 仅薄封装 IO/平台分派/降级，不自研算法 | C3 |
| `productflow/scripts/server.py` | WS 频道加 `spec`；`_auto_stage` ⑥ prompt 追加（compile + 自纠指令）；`_auto_fidelity` 后台裁判 agent（可选，仿 `_auto_arch`） | A7 / C2 / C5 |
| `openai-image-gen`（手册/模板） | 营销页素材 prompt 模板（只出素材、非整页） | B5 |
| `web/src/*`（后期） | 操作台 fidelity 差异图展示（接 P6-5 对比视图旁）；可选 spec 视图 | C3 |
| `references/phase-1~6-*.md` + `AGENTS.md` | E1 各阶段改动，双轨同步 | E1 |

---

## E3. 分期路线（每期独立可发版可验证，一期一个 minor）

| 期 | 版本 | 内容 | 交付即可验证 |
|---|---|---|---|
| **一** | 2.28 | **地基**：`design-spec` 数据结构 + `spec` CLI + `token_compile.py` + `spec check` + 组件目录格式 + 全套单元/CLI 测试 | 纯基础设施、不改流水线行为，可先发；`spec compile` 出三端 token 可独立验证 |
| **二** | 2.29 | **②③**：萃取 token + `choice` 锁库 + 组件目录生成 + 首图反萃取。手册 ②③ 改 | 跑 ②③ 后 `design-spec` 有 tokens+lib+catalog |
| **三** | 2.30 | **④⑤**：token 定稿 + 组件映射 + sidecar + 营销页素材 + 9 态/数据态。手册 ④⑤ 改 | `spec show` 有完整 pages[]（components/states/assets） |
| **四** | 2.31 | **⑥ 验收**：环境确定性 + 三层闸门（裁判/diff/断言）+ pre-flight + 硬闸。手册 ⑥ 改 + `fidelity_diff.py` + `_auto_fidelity` | ⑥ 出 `fidelity-<page>.json` + 差异图，硬闸生效 |
| **五** | 2.32 | **⑥ 自纠闭环**（3 轮护栏）+ ① 竞品图/候选库萌芽 + 打磨 | 自纠自动收敛、护栏（只接受改进）可测 |

**依赖**：地基（一期）必须先行；越往后越依赖前面。自纠闭环（最重）放最后。每期可独立回退。

---

## E4. 测试策略

- **每期保持 171+ 测试全绿**（`python3 -m unittest discover -s tests`），走 `helpers.make_home` 沙箱、subprocess + HOME 覆盖。
- **一期**：`test_pf_state.py` 加 `spec *` CLI 往返；`test_token_compile.py`（新）三端输出断言 + alias 解析 + 成环报错 + dark override；`spec check` 各负例（悬空 alias/成环/缺 lib/page 不对齐）非 0 退出。
- **二~三期**：`choice` 锁库往返、`spec set-tokens/set-page` 往返、`spec check` 缺 catalog/缺态负例。
- **四~五期**：`fidelity_diff` 归一化/差异比例单元测；裁判 `fidelity-<page>.json` schema 往返；自纠护栏「只接受改进才前进」单元测；DOM 断言并入 e2e 套件。
- e2e 层（playwright/chromium）缺依赖时自动 skip（沿用现状）。

---

## E5. 风险与回退

- **向后兼容**：老项目无 `design-spec.json` → `_load_spec` 返回空骨架、⑥ 回退 `direction.md` 文字路径，**不硬报错**（专题 A8/B6/C8 降级）。
- **迁移**：`state.json` 已有 `v` 迁移位；`design-spec.json` 首版带 `v:1`。
- **Pillow 依赖**：`fidelity_diff` 用 Pillow（与 redraw 一致）；无则跳过软证据层。
- **手册双轨**：每期同步 `SKILL.md`/`references` 与 `AGENTS.md`。
- **choice 锁库**：全自动模式必须有自动兜底（不能卡等用户）。

---

## E6. 版本号同步（项目约定）

每期同步三处：`productflow/VERSION` + `SKILL.md` frontmatter `version:` + commit `feat(scope): 描述 (x.y.z)`；scope 用阶段编号或 `spec`/`token`/`fidelity` 等。

---

## E7. 一页速览（实施顺序）

```
一期 2.28  地基: design-spec + spec CLI + token_compile + spec check          [不改流水线]
二期 2.29  ②③: 萃取token + choice锁库 + 组件目录 + 首图反萃取                [手册②③]
三期 2.30  ④⑤: token定稿 + 组件映射 + sidecar + 营销素材 + 9态/数据态         [手册④⑤]
四期 2.31  ⑥验收: 环境确定 + 三层闸门 + pre-flight + 硬闸 + fidelity_diff      [手册⑥ + 新脚本]
五期 2.32  ⑥自纠: 3轮护栏闭环 + ①竞品图/候选库 + 打磨                         [收尾]
```
