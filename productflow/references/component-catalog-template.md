# 组件目录模板（component catalog）

> ② 找参考阶段**锁定组件库后**，按本模板为项目生成 `artifacts/phase-2/component-catalog.md`——作为 ④ 组件映射、⑥ 前端实现「用哪个组件」的**单一事实来源**（借鉴 Halodoc `DS_AGENTS.md` / v0 registry；还原度方案专题 B）。
> 机器可读部分**对齐 shadcn `registry.json` / v0 registry spec**（AI 生态已熟悉、v0 等原生消费的格式），不自创。

## 使用说明

- **只列本项目会用到的组件**（按 ④ 页面清单 + 产品类型裁剪，不必全库照搬）。
- 每条含：`import` / 各平台等价 / 用途 / variants / props / 关联 token / 层级 `level` / 什么场景用。
- **`level` 用于 ⑥ 映射优先级**：`organism` > `molecule` > `atom`——⑥ 优先用高层组件，匹配不上就**报缺口、不静默用最近似的**（静默近似 = 还原度差之源）。
- token 引用 `design-spec.tokens` 的路径（如 `color.action.primary`），⑥ 用编译出的 token 套，不硬编码。

## 组件条目格式

```
### <ComponentName>
- **import**（Web）：`import { X } from "@/components/ui/x"`
- **iOS 等价**：SwiftUI `...`
- **Android 等价**：Compose `...`
- **level**：atom | molecule | organism
- **用途**：一句话
- **variants**：v1(说明) / v2 / …
- **props**：prop(取值) / …
- **token**：背景=color.action.primary，圆角=radius.md，…
- **什么场景用**：…；**不要**用于：…
```

## 示例（shadcn/ui + Tailwind，产品 UI）

### Button
- **import**：`import { Button } from "@/components/ui/button"`
- **iOS 等价**：`Button(action:){ Text() }.buttonStyle(.borderedProminent)`（primary）
- **Android 等价**：`Button(onClick){ Text() }`
- **level**：atom
- **用途**：主行动号召 / 操作触发
- **variants**：default(主 CTA) / secondary / outline / ghost / destructive
- **props**：size(sm|default|lg) / disabled / asChild
- **token**：背景=color.action.primary，文字=color.action.onPrimary，圆角=radius.md
- **什么场景用**：表单提交、CTA、对话框确认；**不要**用于纯页面跳转（用 Link / NavigationLink）

### Card
- **import**：`import { Card, CardHeader, CardContent } from "@/components/ui/card"`
- **iOS 等价**：`VStack{…}.background(…).cornerRadius(…)` 或自定义 CardView
- **Android 等价**：`Card { Column {…} }`（Material3）
- **level**：molecule
- **用途**：内容分组容器（列表项 / 信息块）
- **variants**：default / outlined / elevated
- **props**：—（组合 Header/Content/Footer 子组件）
- **token**：背景=color.surface.default，圆角=radius.md，阴影=shadow.card
- **什么场景用**：卡片列表、信息分组；数据容器需给 empty/loading 态（见专题 D）

### Input
- **import**：`import { Input } from "@/components/ui/input"`
- **iOS 等价**：`TextField(…)`
- **Android 等价**：`OutlinedTextField(…)`（Material3）
- **level**：atom
- **用途**：单行文本输入
- **variants**：default / error
- **props**：type / placeholder / disabled
- **token**：边框=color.border.default，圆角=radius.md，文字=color.text.body
- **什么场景用**：表单字段；必须给 default/focus/disabled/error 态（见专题 D）

## 机器可读补充（对齐 shadcn registry.json；⑥ 可程序化消费）

```json
{
  "name": "project-component-catalog",
  "components": [
    {
      "name": "Button", "level": "atom",
      "variants": ["default", "secondary", "outline", "ghost", "destructive"],
      "props": {"size": ["sm", "default", "lg"], "disabled": "bool"},
      "tokens": {"bg": "color.action.primary", "radius": "radius.md"},
      "web": "@/components/ui/button", "ios": "SwiftUI.Button", "android": "Compose.Button"
    }
  ]
}
```
