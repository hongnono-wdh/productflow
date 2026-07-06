# 还原度方案 · 专题 A — design-spec 数据规范 与 自研 token 编译器

> 本专题把主纲 §3「还原度脊椎」细化到**可直接编码**。对齐现有接口事实（8 阶段流水线、`pf_state.py` CLI 风格、`.productflow/` 数据文件、`_atomic_write_json`、纯 Python 标准库零依赖铁律）。
> 属**第一期**核心。配套：[专题 B 组件库全链路]、[专题 C ⑥ 验收]。

---

## A0. 定位

`design-spec` 是「还原度脊椎」——一份贯穿 ①→⑥ 的**结构化视觉规格单一事实源**，逐级加精（①萌芽→②萃取→③加精→④定稿→⑤补状态→⑥引用）。它替代现在「direction.md 文字 + PNG 幻想图」这套有损传递。**渐进落地（已定决策）**：④ 仍出 PNG 预览，`design-spec.pages[]` 作结构化 sidecar，⑥ 主读它。

---

## A1. 文件与存储（对齐现有约定）

- **物理位置**：`.productflow/design-spec.json`，与 `state.json`/`pages.json`/`explore.json` 并列。
- **读写**：新增 `_load_spec(d)`（仿 `_load_pages`/`_load_explore`，缺文件返回带默认字段的空骨架），写用现有 `_atomic_write_json`。
- **前端推送**：`server.py` 的 WS 频道白名单加 `"spec"`（对标现有 `pages` 频道，前端 `useChannel('spec')` 订阅）。
- **编译产物**：token 编译出的三端文件落 `artifacts/phase-6/tokens/`（`tokens.css` / `Tokens.swift` / `Tokens.kt`），并作 artifact 登记。
- **版本**：`design-spec.json` 带 `"v": 1`（迁移位）+ `"updated"`（复用 `_now()`）。

---

## A2. 完整 Schema（每字段标注 who/when 写入）

```jsonc
{
  "v": 1,
  "updated": "2026-07-03 16:00:00",

  // ── 组件库锁定：②b 写（详见专题 B） ──
  "componentLib": {
    "PC":  { "lib": "shadcn/ui + tailwind", "theme": "neutral", "catalog": "artifacts/phase-2/component-catalog.md" },
    "H5":  { "lib": "shadcn/ui + tailwind", "theme": "neutral", "catalog": "artifacts/phase-2/component-catalog.md" },
    "APP": { "lib": "SwiftUI(HIG) | Material3(Compose)", "theme": "", "catalog": "..." }
  },

  // ── 设计 token：②萃取草案 → ③首图反萃取加精 → ④定稿。DTCG 骨架 + 简化 value，两层为主 ──
  "tokens": {
    "color": {
      "blue":  { "500": { "$value": "#3498db", "$type": "color" } },          // primitive：纯描述，禁语义词
      "gray":  { "100": { "$value": "#f3f4f6", "$type": "color" } },
      "action":{ "primary": { "$value": "{color.blue.500}", "$type": "color" } }, // semantic：表意，引用 primitive
      "surface":{ "default": { "$value": "{color.gray.100}", "$type": "color" } },
      "text":  { "body": { "$value": "#1a1a1a", "$type": "color" } }
    },
    "space":  { "4": { "$value": "16px", "$type": "dimension" } },
    "radius": { "md": { "$value": "8px", "$type": "dimension" } },
    "shadow": { "card": { "$value": "0 1px 3px rgba(0,0,0,.1)", "$type": "shadow" } },
    "font":   { "title": { "$value": "Montserrat", "$type": "fontFamily" },
                "body":  { "$value": "Inter", "$type": "fontFamily" },
                "size":  { "h1": { "$value": "40px", "$type": "dimension" },
                           "body": { "$value": "16px", "$type": "dimension" } } }
  },

  // ── 每页规格：④ 写 components/assets；⑤ 补 states（详见专题 D）。id 对齐 pages.json 的 pg-xxx ──
  "pages": [
    {
      "id": "pg-1a2b3c",                    // == pages.json 同页 id
      "type": "product",                    // product | marketing
      "components": [                        // ④ 出「设计元素→组件」映射（详见专题 B）
        { "slot": "hero.cta", "lib": "Button", "variant": "primary", "props": { "size": "lg" } },
        { "slot": "list", "lib": "Card", "variant": "default" }
      ],
      "states": {                           // ⑤ 补：组件/页面的状态矩阵（详见专题 D）
        "list": ["default", "empty", "loading"],
        "CTAForm": ["default", "submitting", "error", "success"]
      },
      "assets": [                           // 营销页专用：只生图的独特素材（详见专题 B）
        { "slot": "hero.bg", "gen": "gpt-image", "file": "artifacts/phase-4/pg-1a2b3c-hero-bg.png" }
      ]
    }
  ],

  // ── 溯源：②③ 写，可审计 token 从哪来 ──
  "provenance": {
    "refs": ["ref-abc123"],                 // ② token 萃取自哪些参考图
    "hero": "artifacts/phase-3/heroes/1.png", // ③ 首图反萃取来源
    "heroPrompt": "…"                        // ③ 生成指令留痕
  }
}
```

**两层 token 纪律（校验强制）**：primitive 层（`color.blue.500`）纯描述、禁 `primary/error/brand` 等语义词；semantic 层（`color.action.primary`）用 `{alias}` 引用 primitive；component 层（`button.bg`）**按需才加**，不预铺。

---

## A3. 新增 CLI：`pf_state.py spec ...`（对齐现有子命令风格）

```
spec show                                          # 打印 design-spec.json
spec set-lib   --platform <PC|H5|APP> --lib <str> --theme <str> [--catalog <path>]
spec set-token <path> --value <v> [--type color|dimension|shadow|fontFamily] [--ref]
                                                   # path 如 color.action.primary；--ref 表示 value 是 {alias}
spec set-tokens --file <tokens.json>               # 批量导入（②萃取时一次性写入草案）
spec set-page  <pg-id> --type <product|marketing>
                       [--component <slot:lib:variant>]...   # 可重复
                       [--state <comp:s1,s2,...>]...         # 可重复
                       [--asset <slot:gen:file>]...          # 可重复
spec compile   --platform <PC|H5|APP|all> --out <dir>        # 调 token 编译器，见 A4
spec check                                          # 结构校验，见 A5；缺陷则非 0 退出
```

- 每个写命令末尾 `_atomic_write_json` + 追加一条 `state.log`（复用现有模式）。
- `spec set-page` 的 `--component slot:lib:variant`、`--state comp:s1,s2`、`--asset slot:gen:file` 用**冒号/逗号分隔的紧凑串**（照 `page set --add-version file --platform PC` 的既有紧凑风格），parser 里 split 解析。
- 幂等：`set-token`/`set-lib`/`set-page` 同 key 覆盖、不追加。

---

## A4. 自研 token 编译器 `productflow/scripts/token_compile.py`（纯 stdlib）

> **为何自研而非用 Style Dictionary（已评估拍板）**：Style Dictionary 是行业标准、覆盖三端，但它是 **Node**——引入它给流水线加整个 Node runtime 依赖，违背「端上零三方依赖」铁律（iOS/Android 项目机器常无 Node）。而 token 编译这个「轮子」极小（名字转换 + 值转换 + alias 解析，几十行、无算法难点、极好测试），**自研成本 < 引入重依赖**。这是「轮子太小、造比买划算」的少数情况，故保持自研。（对比：diff 算法复杂、有开源标准 → 用开源，见专题 C。）

**定位**：一份 `tokens` → Web/iOS/Android 三端代码。让「三端一致」成为编译产物，不靠 AI 自觉。`__file__` 自定位、零三方依赖，可被 `spec compile` 调用、也可被 ⑥ agent 直接 `python3 token_compile.py`。

**核心逻辑：**

1. **展平 + 解析 alias**：递归遍历 `tokens` 树，path 拼成点串（`color.action.primary`）；遇 `$value` 是 `{alias}` 则递归解析到终值（防环：解析栈查重，成环报错）。
2. **命名转换**：
   | 平台 | path 规则 | 例（`color.action.primary`） |
   |---|---|---|
   | Web CSS | kebab，`--` 前缀 | `--color-action-primary` |
   | iOS Swift | camelCase（去 color 前缀可选） | `actionPrimary` |
   | Android Compose | PascalCase | `ActionPrimary` |
3. **值转换（按 `$type`）**：
   | $type | Web | iOS Swift | Compose |
   |---|---|---|---|
   | color `#3498db` | `#3498db` | `Color(hex: "3498db")` | `Color(0xFF3498DB)` |
   | dimension `16px` | `16px`（另出 `--x-rem`）| `CGFloat(16)` | `16.dp` |
   | fontFamily `Inter` | `'Inter'` | `.custom("Inter", …)` | `FontFamily(…)` |
   | shadow | `box-shadow` 值 | 注释/`.shadow(…)` | 注释/`Modifier.shadow` |
4. **输出模板**：
   - Web：`:root { --color-action-primary: #3498db; ... }`（dark 模式：semantic override → `@media (prefers-color-scheme:dark)`）
   - iOS：`import SwiftUI\nextension Color { static let actionPrimary = Color(hex:"3498db") } ...`（附 `Color(hex:)` 扩展）
   - Compose：`object Tokens { val ActionPrimary = Color(0xFF3498DB); val Space4 = 16.dp; ... }`

**CLI**：`python3 token_compile.py --spec <design-spec.json> --platform <PC|H5|APP|all> --out <dir>` → 写 `tokens.css`/`Tokens.swift`/`Tokens.kt`。

---

## A5. `spec check` 校验规则（进闸前拦结构错）

1. **悬空 alias**：`{color.x.y}` 引用不存在的 token → 报错。
2. **成环 alias**：A→B→A → 报错。
3. **primitive 禁语义词**：primitive 层 key 出现 `primary/secondary/error/success/brand` → 警告（可 `--strict` 升为错）。
4. **缺 lib**：`componentLib` 里 scope 选定的平台没锁 lib → 报错（挡住 ⑥ 裸写，与专题 B 的 pre-flight 门呼应）。
5. **page id 对齐**：`pages[].id` 必须存在于 `pages.json` → 报错。
6. **type 合法**：`pages[].type ∈ {product, marketing}`。
返回码：有 error → 非 0（可被 ⑥ 硬闸 `phase 6 --status done` 引用，同现有 `impl-check` 模式）。

---

## A6. 各阶段写入时序（谁在什么时候动 design-spec）

| 阶段 | 动作 | 命令 |
|---|---|---|
| ① 市场调研 | 起骨架 + 候选库 | `spec set-lib`（候选，profile 推断） |
| ② 找参考 | 萃取 token 草案 + 锁库 | `spec set-tokens --file`（萃取结果）、`spec set-lib`（锁定，专题 B） |
| ③ 首图 | 反萃取加精 token | `spec set-token color.* --value <真实hex>` |
| ④ 页面设计 | 定稿 token + 每页组件映射 + 营销页素材 | `spec set-token`（定稿）、`spec set-page --component/--asset` |
| ⑤ 功能数据 | 补状态矩阵 | `spec set-page --state`（专题 D） |
| ⑥ 前端实现 | 编译 token + 引用 | `spec compile --platform all --out ...`（scaffold 后），frontend import |

---

## A7. 集成到 ⑥ 前端实现（8 阶段：⑥=phase-6-frontend.md）

1. `scaffold` step 后：`spec check` → `spec compile --platform all` → 三端 token 文件进项目、artifact 登记。
2. `frontend` step：import token 文件（Web CSS var / iOS `Color.actionPrimary` / Compose `Tokens.*`），组件按 `pages[].components` 映射拼（专题 B），**不硬编码色值/间距**。
3. `server.py._auto_stage` 给 ⑥ 的 prompt 追加一句：「先 `spec check` + `spec compile`，用编译出的 token 文件，不要肉眼从设计稿猜色值」。

---

## A8. 向后兼容与降级

- **无 design-spec.json**（老项目 / 未跑新②③④）：`spec compile` 早退、⑥ 回退现有「读 `direction.md` 文字 + PNG」路径，**不硬报错**（沿用项目「优雅降级」惯例）。
- **部分 token 缺失**：编译器只编已有的，缺的由 ⑥ 回退 direction.md 兜底并 `log` 提示。

---

## A9. 测试点（对齐 tests/ 沙箱）

- `test_pf_state.py`：新增 `spec set-lib/set-token/set-page/show/check` 的 CLI 往返测试（`cli`/`cli_json` + `make_home` 沙箱）。
- `test_token_compile.py`（新）：喂一份含 primitive+semantic+alias+dimension 的样例 `tokens`，断言三端输出的关键行（`--color-action-primary: #3498db`、`Color(hex:"3498db")`、`Color(0xFF3498DB)`、`16.dp`）、alias 解析、成环报错、dark override。
- `spec check`：悬空 alias / 成环 / 缺 lib / page id 不对齐 各一条负例断言非 0 退出。

---

## A10. 落地清单（第一期）

- [ ] `pf_state.py`：`_load_spec` + `cmd_spec` + argparse `spec` 子命令（A3）
- [ ] `productflow/scripts/token_compile.py`：编译器（A4）
- [ ] `server.py`：WS 频道加 `spec`；`_auto_stage` ⑥ prompt 追加编译指令（A7）
- [ ] `spec check` 校验（A5）
- [ ] 测试（A9）
- [ ] `design-spec.json` 迁移：老项目缺文件时 `_load_spec` 返回空骨架（A8）
- 手册改动（②③④⑥ 各写入时序）见**专题 E**。
