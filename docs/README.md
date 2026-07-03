# ProductFlow 项目文档索引

> 本目录由 **understand-anything** 分析流程产出，帮助工程师在改造前吃透项目。
> 分析时间：2026-07-01 · 分析范围：88 个源文件（已排除 `针对这个项目的需求改造/` 同事文件夹、
> `openai-image-gen/templates/` 生图模板、构建产物）。

## 一句话

**ProductFlow 是一套 Claude Code skill 集合 + 本地操作台（`localhost:7717`）**，把「做一个互联网产品」变成 7 阶段可视化流水线（①市场调研→②找参考→③首图→④页面→⑤功能与数据→⑥开发→⑦部署）。**仓库本身是工具，不是用它生产出来的产品。**

## 文档地图

| 文档 | 读它来… |
|------|---------|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | 吃透架构：双入口+单一状态源、三大支柱（pf_state.py/server.py/PF_HOME）、状态数据模型、API 面、前端、测试、安全边界、关键不变量 |
| [`ONBOARDING.md`](./ONBOARDING.md) | 新人上手：半小时跑起来、仓库地图、三条开发回路、测试、提交约定、第一个改动、避坑清单 |
| [`DOMAIN.md`](./DOMAIN.md) | 业务流程：7 阶段流水线的领域建模、项目生命周期、状态协议、视觉设计生产、质量保障、部署上线 |

## 交互式知识图谱

understand-anything 生成的知识图谱在 `.understand-anything/knowledge-graph.json`：

- **286 节点**（62 file / 169 function / 29 class / 22 document / 4 config）
- **630 边**（imports / contains / calls / exports / documents / configures / tested_by / depends_on…）
- **9 个架构层**：编排与阶段手册 · 状态机与操作台后端 · 安装与运维脚本 · 操作台前端 · 生图引擎 · 官网落地页 · 测试与质量验证 · 配套命令 Skills · 项目文档与元数据
- **13 步导览**：从「这是工具不是产品」到落地页，逐层讲透

可视化浏览（交互式 dashboard）：

```
/understand-dashboard
```

对代码库提问 / 深挖某个文件：

```
/understand-chat            # 问「支付流程怎么走」这类问题
/understand-explain <路径>  # 深挖某个文件/函数/模块
/understand-diff            # 改完代码评估影响面
```

## 权威来源（代码里的一手资料）

- `productflow/SKILL.md` —— 7 阶段编排大脑（含状态协议、检查点节奏、降级表）
- `productflow/scripts/pf_state.py` —— 状态机（`PHASES` 是 7 阶段×步骤的权威定义）
- `productflow/scripts/server.py` —— 操作台后端（HTTP+WS、后台 spawn agent、inpaint、密钥）
- `productflow/references/phase-N-*.md` —— 各阶段操作手册
- 根 `README.md` / `CLAUDE.md` —— 安装与仓库约定

## 维护本套文档

代码演进后，增量刷新知识图谱（只重分析改动文件）：

```
/understand            # 增量更新 .understand-anything/knowledge-graph.json
```

> 注：understand-anything 的合并脚本需 **Python 3.10+**（本机用 `python3.11`）；
> 图谱构建依赖已装好的 pnpm + 编译过的 tree-sitter 解析器（见 `.understand-anything/`）。
