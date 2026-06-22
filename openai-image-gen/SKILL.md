---
name: openai-image-gen
description: Batch-generate images via OpenAI Images API (gpt-image series). One subject × N different visual styles (styles.json presets) + 94 个场景化提示词模板（UI mockup / 落地页长图 / 海报 / 信息图 / 品牌板等 17 类，templates/）. Use whenever the user wants AI images in bulk, landing-page hero mockups, UI concept images, full-page UI 样机, or "生成 N 张不同风格的图".
---

# OpenAI Image Gen

Generate batches of images via the OpenAI Images API. Three modes:

1. **Subject × styles**（推荐）：一个主题，自动配 N 种**不同**风格（风格池在 `styles.json`）
2. **Explicit prompts**：`--prompt` 重复传参，逐条生成
3. **Random sampler**：无参数时随机"结构化"提示词

## Setup

- Needs env: `OPENAI_API_KEY`（或 `--api-key`）
- 默认模型 `gpt-image-1.5`；要用 GPT Image 2 的文字渲染优势（UI mockup 里直接写 headline/价格文案）传 `--model gpt-image-2`

## Run

```bash
SKILL=~/.claude/skills/openai-image-gen

# 看有哪些风格
python3 $SKILL/scripts/gen.py --list-styles

# "生成 10 张不同风格的落地页主图"
python3 $SKILL/scripts/gen.py --subject "landing page hero for a meditation app, headline 'Breathe'" \
  --count 10 --category web-design --model gpt-image-2

# 指定风格（count 自动 = 风格数）
python3 $SKILL/scripts/gen.py --subject "pricing page for an AI notes app" \
  --style dark-pricing-page --style glassmorphism-ui --style swiss-international

# 自定义 prompt / 随机模式（旧用法不变）
python3 $SKILL/scripts/gen.py --prompt "ultra-detailed studio photo of a lobster astronaut" --count 4
python3 $SKILL/scripts/gen.py --count 8

# 先 --dry-run 预览 prompt（不花钱），确认后再去掉
python3 $SKILL/scripts/gen.py --subject "..." --count 10 --dry-run
```

输出目录优先 `~/Projects/tmp/openai-image-gen-<stamp>/`（不存在则 `./tmp/...`），含 `*.png` + `prompts.json`（prompt/style ↔ 文件映射）+ `index.html` 画廊。生成后 `open .../index.html` 给用户看。

## styles.json 风格库

每条风格：`id`（kebab-case 唯一）、`category`（`web-design` 网页设计风格 / `ui-mockup` UI 概念图模板 / `art` 艺术风格）、`prompt`（风格描述片段，拼接为 `{subject}. Style: {prompt}.`）、`notes`（适用场景，中文）。

`ui-mockup` 类源自 `productflow` 项目的 GPT Image 2 提示词库（`gpt-image-2-ui-prompts.md`），遵循其结构公式：**[设备/载体] + [产品类型] + [布局] + [具体文字] + [配色] + [视角]**。要点：mockup 一词必须保留；标题/价格等文案直接写进 prompt（英文），GPT Image 2 渲染文字可靠。

## templates/ 场景模板库（94 个，17 类）

风格轴之外的第二个轴：**场景化结构模板**（同步自 garden-skills，MIT，见 `templates/ATTRIBUTION.md`）。风格轴管"什么视觉风格"，场景轴管"什么类型的图"——UI 生产两者配合用，速查表在 **`templates/UI-FOCUS.md`**（按需求映射到具体模板/风格，必读）。

用法：`templates/INDEX.md` 找模板 → Read 模板全文 → 按模板的"缺失信息提问顺序"补齐 → 填 `{argument}` 槽位渲染完整英文 prompt → `gen.py --prompt "<渲染结果>"`。重点模板：`ui-mockups/landing-page-case-study.md`（完整落地页长图，hero→数据→证言→CTA）。

新场景沉淀成模板的方法论见 `templates/prompt-writing.md`；上游再同步的命令在 `templates/ATTRIBUTION.md`（本地新增的 INDEX/UI-FOCUS/ATTRIBUTION 三个文件不参与覆盖）。

## 扩展风格库（AI 自更新机制）

当用户说"加一种 XX 风格"、生成结果风格不够多样、或你在网上看到新的设计趋势时，**直接编辑 `styles.json` 追加条目**，不要改代码：

1. 新条目放进 `styles` 数组：`id` 用 kebab-case 且不与现有重复；`prompt` 用英文、只写风格描述（材质/排版/配色/光线/视角），**不含具体主题**；`notes` 用中文写适用场景
2. 来源建议：用户给的参考图（先总结其风格要素再写成 prompt）、WebSearch 当年的 web design trends（如 "2026 web design trends"）、Dribbble/Awwwards 热门风格名词
3. 新风格先 `--dry-run` 看拼接效果，再小批量（`--count 2 --quality low`）实测，效果差就改 prompt 重试
4. 项目级定制：把 `styles.json` 拷到项目里改，运行时 `--styles-file <path>` 指向它，不污染全局库
