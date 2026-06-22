# UI 生产专用导航

本 skill 有两个互补的轴，UI 生产时按需求选轴：

- **风格轴** `styles.json`（CLI 直接组合）：同一主题快速出 N 张**互不相同**视觉风格 → 适合发散探索、让用户挑方向
- **场景轴** `templates/`（94 个结构化模板）：读模板 → 填 `{argument}` 槽位 → 渲染完整 prompt → `gen.py --prompt "..."` → 适合方向已定、要某个**具体 UI 场景**的高质量成图

## 按 UI 需求速查

| 需求 | 用什么 |
|------|--------|
| 风格还没定，先看 N 个方向 | `--subject "..." --count N --category web-design`（风格轴，唯一能一条命令保证 N 风格不重复） |
| 完整落地页长图（hero→数据→证言→CTA） | `ui-mockups/landing-page-case-study.md` ⭐ |
| 落地页 hero 单屏 | `poster-and-campaigns/banner-hero.md`，或风格轴 `light-marketing-hero` / `aurora-gradient-mesh` |
| 定价页 | 风格轴 `dark-pricing-page` |
| SaaS 仪表盘概念图 | 风格轴 `saas-dashboard-mockup` / `isometric-saas` |
| 功能总览区块 | `infographics/bento-grid-infographic.md`，或风格轴 `bento-grid` |
| 移动端 App 概念 | 风格轴 `mobile-app-concept`；聊天类 UI 用 `ui-mockups/chat-interface-scene.md` |
| 电商/直播/商品卡 UI | `ui-mockups/live-commerce-ui.md` / `product-card-overlay.md` / `short-video-cover-ui.md` |
| 品牌方向板 | `branding-and-packaging/brand-identity-board.md`，或风格轴 `brand-style-tile` / `design-system-sheet` |
| 多方案塞进一张图对比 | `grids-and-collages/mixed-style-multi-panel.md`（同主题多风格单图）/ `banner-grid-2x2.md` |
| 产品实物配图 | `product-visuals/`（白底主图/影棚/生活方式场景/爆炸图） |

## 模板用法（场景轴）

1. 在 `INDEX.md` 找到模板 → Read 模板全文（含"何时使用/不要使用/缺失信息提问顺序"）
2. 按模板的提问顺序补齐信息（用户在场就问，全自动就按上下文填并记录假设）
3. 填 `{argument name="..." default="..."}` 槽位渲染成完整英文 prompt
4. `python3 scripts/gen.py --prompt "<渲染结果>" --model gpt-image-2`
5. 同一模板要多风格变体：把风格轴 styles.json 的 prompt 片段替换模板的配色/风格槽位，逐张生成

## 两轴融合（提示词持续优化为 UI 专用）

- 模板里出现的好风格描述 → 按 `styles.json` 条目格式抽出来回填风格库（见 SKILL.md「扩展风格库」）
- 反复出现的新 UI 场景 → 按 `templates/prompt-writing.md` 的方法论沉淀成新模板，放进对应分类并更新 INDEX.md
